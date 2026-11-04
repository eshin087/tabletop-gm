"""Validators: seed, packs, org plan, outline and exercise pack.

Each returns a Result with errors (build fails) and warnings (build continues,
outputs carry a banner). The checks enforce the guardrails in the spec:

- every clock has a source URL, a verified date, and a tier
- researched-tier clocks are flagged
- every inject cites a finding ID from the seed or a labeled assumption
- every org plan item carries a verbatim quote found in its source document
- escalation rules hold across the inject set
- nothing is built before human approval
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .common import as_list, canonical_hash, read_text, read_yaml
from .packs import REQUIRED_PACK_HEADINGS, load_pack, packs_dir, COMMON_FILE
from .plan_ingest import verify_org_plan

TIERS = {"verified", "researched"}
PHASES = ["detection", "escalation", "containment", "recovery", "notification"]
INJECT_COUNT = {60: 5, 90: 7, 180: 10}
INJECT_REQUIRED = [
    "id", "order", "phase", "time_marker", "title", "what_happens", "recipients",
    "decision_forced", "decision_owner_role", "procedure_tested", "what_good_looks_like",
    "where_teams_fail", "expected_actions", "hints", "host_lines", "source",
]
SEVERITY_MUSTS = {
    1: ["alert", "escalation"],
    2: ["money_or_data_decision", "legal"],
    3: ["outage", "ransom_note", "restore_order"],
    4: ["three_pressures", "public_statement"],
}
APPROVAL_FIELDS = ("approved", "approved_by", "approved_at", "outline_hash")


@dataclass
class Result:
    subject: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {"subject": self.subject, "ok": self.ok, "errors": self.errors, "warnings": self.warnings, "info": self.info}

    def summary(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        lines = [f"[{status}] {self.subject}: {len(self.errors)} error(s), {len(self.warnings)} warning(s)"]
        lines += [f"  error: {e}" for e in self.errors]
        lines += [f"  warning: {w}" for w in self.warnings]
        return "\n".join(lines)


def _is_url(value: Any) -> bool:
    return isinstance(value, str) and re.match(r"^https?://[^\s]+$", value) is not None


def _is_date(value: Any) -> bool:
    if isinstance(value, (date, datetime)):
        return True
    if isinstance(value, str):
        try:
            date.fromisoformat(value[:10])
            return True
        except ValueError:
            return False
    return False


# --------------------------------------------------------------------------- #
# Seed
# --------------------------------------------------------------------------- #

def validate_seed(seed: dict) -> Result:
    r = Result("seed")
    for key in ("entry", "pivot", "target", "path_source", "source", "findings_cited", "assumptions"):
        if key not in seed:
            r.error(f"missing key '{key}'")
    if r.errors:
        return r
    for part in ("entry", "pivot", "target"):
        node = seed[part]
        if not node.get("rule"):
            r.error(f"{part} has no selection rule recorded")
        if not node.get("asset"):
            r.error(f"{part} has no asset")
        if node.get("rule") == "assumption" and not node.get("assumption"):
            r.error(f"{part} is an assumption but carries no assumption id")
    assumption_ids = {a.get("id") for a in seed.get("assumptions", [])}
    for part in ("entry", "pivot", "target"):
        aid = seed[part].get("assumption")
        if aid and aid not in assumption_ids:
            r.error(f"{part} cites assumption '{aid}' that is not in the assumptions list")
    cited = seed.get("findings_cited", [])
    if len(cited) > 3:
        r.error(f"{len(cited)} findings cited; the limit is three")
    for part in ("entry", "pivot", "target"):
        fid = seed[part].get("finding_id")
        if fid and fid not in cited:
            r.error(f"{part} finding {fid} not listed in findings_cited")
    if seed["path_source"] not in {"tenable_apa", "inferred"}:
        r.error(f"path_source must be tenable_apa or inferred, got '{seed['path_source']}'")
    if seed["entry"].get("finding_id") and seed["entry"].get("internet_facing") is not True:
        r.error("entry finding is not on an internet-facing asset")
    r.info = {"findings_cited": cited, "assumptions": len(assumption_ids), "source": seed.get("source")}
    return r


# --------------------------------------------------------------------------- #
# Packs and clocks
# --------------------------------------------------------------------------- #

def validate_clock(clock: dict, r: Result, where: str) -> None:
    cid = clock.get("id") or "<no id>"
    label = f"{where} clock '{cid}'"
    for key in ("id", "name", "deadline_text", "source_url", "verified_date", "tier", "citation"):
        if clock.get(key) in (None, ""):
            r.error(f"{label}: missing {key}")
    if not _is_url(clock.get("source_url")):
        r.error(f"{label}: source_url is not an http(s) link")
    if not _is_date(clock.get("verified_date")):
        r.error(f"{label}: verified_date is not an ISO date")
    tier = clock.get("tier")
    if tier not in TIERS:
        r.error(f"{label}: tier must be one of {sorted(TIERS)}")
    elif tier == "researched":
        r.warn(f"{label}: researched tier, verify before exercise")
    if clock.get("deadline_hours") is None and clock.get("deadline_business_days") is None and not clock.get("deadline_text"):
        r.error(f"{label}: no deadline_hours, deadline_business_days, or deadline_text")
    for key in ("deadline_hours", "deadline_business_days"):
        val = clock.get(key)
        if val is not None and (not isinstance(val, (int, float)) or val <= 0):
            r.error(f"{label}: {key} must be a positive number or null")
    cond = clock.get("applies_when") or {}
    allowed = {"industries", "data_types", "countries", "states", "public_company", "flags", "min_affected"}
    for key in cond:
        if key not in allowed:
            r.error(f"{label}: applies_when key '{key}' is not one of {sorted(allowed)}")
    if not re.match(r"^[a-z0-9_]+$", str(cid)):
        r.error(f"{label}: id must be snake_case")


def validate_clocks_file(path: str | Path) -> Result:
    p = Path(path)
    r = Result(f"clocks file {p}")
    try:
        raw = read_yaml(p) or {}
    except Exception as exc:  # yaml errors
        r.error(f"cannot parse YAML: {exc}")
        return r
    if "pack" not in raw:
        r.error("missing 'pack'")
    ids: set[str] = set()
    for clock in raw.get("clocks") or []:
        validate_clock(clock, r, raw.get("pack", "?"))
        cid = clock.get("id")
        if cid in ids:
            r.error(f"duplicate clock id '{cid}'")
        ids.add(cid)
    for req in raw.get("exercise_requirements") or []:
        rid = req.get("id") or "<no id>"
        for key in ("id", "name", "requirement", "source_url", "tier", "verified_date", "citation"):
            if req.get(key) in (None, ""):
                r.error(f"exercise requirement '{rid}': missing {key}")
        if not _is_url(req.get("source_url")):
            r.error(f"exercise requirement '{rid}': source_url is not an http(s) link")
        if req.get("tier") not in TIERS:
            r.error(f"exercise requirement '{rid}': tier must be one of {sorted(TIERS)}")
    r.info = {"clocks": len(raw.get("clocks") or []), "exercise_requirements": len(raw.get("exercise_requirements") or [])}
    return r


def validate_defaults(defaults: dict, r: Result) -> None:
    roles = defaults.get("roles") or []
    if not roles:
        r.error("defaults.yaml has no roles")
    seen = set()
    for role in roles:
        if not role.get("id") or not role.get("name"):
            r.error("defaults.yaml role without id or name")
        if role.get("id") in seen:
            r.error(f"defaults.yaml duplicate role id '{role.get('id')}'")
        seen.add(role.get("id"))
    actions = defaults.get("expected_actions") or {}
    for phase in PHASES:
        if not actions.get(phase):
            r.error(f"defaults.yaml has no expected_actions for phase '{phase}'")
    action_ids = set()
    for phase, items in actions.items():
        for a in items or []:
            if not a.get("id") or not a.get("text"):
                r.error(f"defaults.yaml expected action in '{phase}' without id or text")
            if a.get("id") in action_ids:
                r.error(f"defaults.yaml duplicate expected action id '{a.get('id')}'")
            action_ids.add(a.get("id"))
    if not defaults.get("notify_parties"):
        r.error("defaults.yaml has no notify_parties")


def validate_pack(slug: str, base=None) -> Result:
    r = Result(f"pack {slug}")
    try:
        pack = load_pack(slug, base)
    except Exception as exc:
        r.error(str(exc))
        return r
    file_result = validate_clocks_file(pack.path / "clocks.yaml")
    r.errors.extend(file_result.errors)
    r.warnings.extend(file_result.warnings)
    if not (pack.path / "defaults.yaml").exists():
        r.error("defaults.yaml missing")
    else:
        validate_defaults(pack.defaults, r)
    if not (pack.path / "pack.md").exists():
        r.error("pack.md missing")
    else:
        for heading in REQUIRED_PACK_HEADINGS:
            if heading not in pack.markdown:
                r.error(f"pack.md missing heading '{heading}'")
        if "—" in pack.markdown:
            r.warn("pack.md contains an em dash")
    r.info = {"clocks": len(pack.clocks), "researched": sum(1 for c in pack.clocks if c.get("tier") != "verified")}
    return r


def validate_all_packs(base=None) -> list[Result]:
    root = packs_dir(base)
    results = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "clocks.yaml").exists() and not child.name.startswith("_"):
            results.append(validate_pack(child.name, base))
    common = root / COMMON_FILE
    if common.exists():
        results.append(validate_clocks_file(common))
    else:
        results.append(Result("clocks_common.yaml", errors=["clocks_common.yaml missing"]))
    # global id uniqueness
    seen: dict[str, str] = {}
    dup = Result("clock ids across packs")
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "clocks.yaml").exists() and not child.name.startswith("_"):
            for c in (read_yaml(child / "clocks.yaml") or {}).get("clocks") or []:
                if c.get("id") in seen:
                    dup.error(f"clock id '{c.get('id')}' defined in both {seen[c['id']]} and {child.name}")
                seen[c.get("id")] = child.name
    if common.exists():
        for c in (read_yaml(common) or {}).get("clocks") or []:
            if c.get("id") in seen:
                dup.error(f"clock id '{c.get('id')}' defined in both {seen[c['id']]} and common")
            seen[c.get("id")] = "common"
    results.append(dup)
    return results


# --------------------------------------------------------------------------- #
# Org plan
# --------------------------------------------------------------------------- #

ORG_PLAN_CATEGORIES = {
    "role", "decision_authority", "severity_level", "escalation_step", "notification_procedure",
    "containment_procedure", "recovery_objective", "playbook_step", "comms_template", "other",
}


def validate_org_plan(org_plan: dict, documents: dict[str, dict] | None) -> Result:
    r = Result("org_plan")
    if "items" not in org_plan or not isinstance(org_plan["items"], list):
        r.error("org_plan has no 'items' list")
        return r
    if not org_plan.get("source_documents"):
        r.error("org_plan has no source_documents")
    ids = set()
    for item in org_plan["items"]:
        iid = item.get("id") or "<no id>"
        if iid in ids:
            r.error(f"duplicate item id '{iid}'")
        ids.add(iid)
        for key in ("id", "category", "label", "quote", "document"):
            if not item.get(key):
                r.error(f"item '{iid}': missing {key}")
        if item.get("category") not in ORG_PLAN_CATEGORIES:
            r.error(f"item '{iid}': category '{item.get('category')}' not in {sorted(ORG_PLAN_CATEGORIES)}")
        if item.get("quote") and len(item["quote"]) < 8:
            r.error(f"item '{iid}': quote shorter than 8 characters")
    for gap in org_plan.get("gaps", []):
        if not gap.get("topic"):
            r.error("gap without a topic")
    if documents is None:
        r.warn("source documents not supplied; quotes were not verified")
    else:
        for res in verify_org_plan(org_plan, documents):
            if not res["ok"]:
                r.error(f"item '{res['id']}': {res['reason']}")
            elif res.get("warning"):
                r.warn(f"item '{res['id']}': {res['warning']}")
    r.info = {"items": len(org_plan["items"]), "gaps": len(org_plan.get("gaps", []))}
    return r


# --------------------------------------------------------------------------- #
# Exercise pack (outline)
# --------------------------------------------------------------------------- #

def approval_hash(pack: dict) -> str:
    """Hash of everything except the approval block itself."""
    body = {k: v for k, v in pack.items() if k != "approval"}
    return canonical_hash(body)


def validate_exercise_pack(pack: dict, require_approval: bool = False) -> Result:
    r = Result("exercise_pack")
    for key in ("title", "organization", "pack", "severity_level", "duration_minutes", "seed", "clocks", "injects", "roles", "approval"):
        if key not in pack:
            r.error(f"missing key '{key}'")
    if r.errors:
        return r

    seed = pack["seed"]
    seed_result = validate_seed(seed)
    for e in seed_result.errors:
        r.error(f"seed: {e}")
    cited = set(seed.get("findings_cited", []))
    assumption_ids = {a.get("id") for a in seed.get("assumptions", [])} | {a.get("id") for a in pack.get("assumptions", [])}

    # clocks
    clock_ids = set()
    for c in pack["clocks"]:
        validate_clock(c, r, "exercise pack")
        clock_ids.add(c.get("id"))
    if not pack["clocks"]:
        r.warn("no notification clocks apply; the notification phase will use pack guidance only")

    # roles
    role_ids = {role.get("id") for role in pack["roles"]}
    if not role_ids:
        r.error("no roles")

    # org plan references
    org_items = {item.get("id"): item for item in (pack.get("org_plan") or {}).get("items", [])}

    # injects
    injects = pack["injects"]
    duration = int(pack["duration_minutes"])
    expected = INJECT_COUNT.get(duration)
    if expected is None:
        r.error(f"duration_minutes must be one of {sorted(INJECT_COUNT)}")
    elif len(injects) != expected:
        r.error(f"{len(injects)} injects for {duration} minutes; expected {expected}")
    severity = int(pack["severity_level"])
    if severity not in SEVERITY_MUSTS:
        r.error("severity_level must be 1 to 4")

    flags_seen = {"conflicting_information": 0, "business_tradeoff": 0, "plan_silent": 0, "starts_clock": 0}
    orders = []
    inject_ids = set()
    for inj in injects:
        iid = inj.get("id") or "<no id>"
        if iid in inject_ids:
            r.error(f"duplicate inject id '{iid}'")
        inject_ids.add(iid)
        for key in INJECT_REQUIRED:
            if key not in inj or inj[key] in (None, "", [], {}):
                r.error(f"inject {iid}: missing {key}")
        if inj.get("phase") not in PHASES:
            r.error(f"inject {iid}: phase '{inj.get('phase')}' not in {PHASES}")
        orders.append(inj.get("order"))
        # source citation
        src = inj.get("source") or {}
        stype, sref = src.get("type"), src.get("ref")
        if stype == "finding":
            if sref not in cited:
                r.error(f"inject {iid}: cites finding '{sref}' that is not in the seed's findings_cited {sorted(cited)}")
        elif stype == "assumption":
            if sref not in assumption_ids:
                r.error(f"inject {iid}: cites assumption '{sref}' that is not labeled in the seed or the pack")
        else:
            r.error(f"inject {iid}: source.type must be 'finding' or 'assumption'")
        # owner role
        if inj.get("decision_owner_role") and inj["decision_owner_role"] not in role_ids:
            r.error(f"inject {iid}: decision_owner_role '{inj['decision_owner_role']}' is not a defined role")
        # procedure tested
        proc = inj.get("procedure_tested") or {}
        ptype = proc.get("type")
        if ptype == "org_plan":
            if proc.get("ref") not in org_items:
                r.error(f"inject {iid}: procedure_tested cites org plan item '{proc.get('ref')}' that does not exist")
            elif not proc.get("quote"):
                r.error(f"inject {iid}: org plan procedure without a verbatim quote")
            elif org_items[proc["ref"]].get("quote") and proc["quote"].strip() not in org_items[proc["ref"]]["quote"]:
                r.error(f"inject {iid}: procedure quote does not match org plan item '{proc['ref']}'")
        elif ptype == "pack_default":
            if not proc.get("ref"):
                r.error(f"inject {iid}: pack_default procedure without a ref")
        elif ptype == "plan_silent":
            flags_seen["plan_silent"] += 1
        else:
            r.error(f"inject {iid}: procedure_tested.type must be org_plan, pack_default, or plan_silent")
        # expected actions
        for a in inj.get("expected_actions") or []:
            if not a.get("id") or not a.get("text"):
                r.error(f"inject {iid}: expected action without id or text")
            if not a.get("source"):
                r.error(f"inject {iid}: expected action '{a.get('id')}' has no source")
        # flags
        fl = inj.get("flags") or {}
        if fl.get("conflicting_information"):
            flags_seen["conflicting_information"] += 1
        if fl.get("business_tradeoff"):
            flags_seen["business_tradeoff"] += 1
        if fl.get("plan_silent") and ptype != "plan_silent":
            flags_seen["plan_silent"] += 1
        for cid in as_list(fl.get("starts_clock")):
            flags_seen["starts_clock"] += 1
            if cid not in clock_ids:
                r.error(f"inject {iid}: starts clock '{cid}' that is not in the pack's clocks")
        # narrative must not carry numbers of hours/days that are not clock deadlines
        _check_narrative_deadlines(inj, pack["clocks"], r)

    if orders != sorted(orders) or len(set(orders)) != len(orders):
        r.error("inject order is not strictly increasing")
    if injects:
        if flags_seen["conflicting_information"] == 0:
            r.error("escalation rule: no inject delivers conflicting information")
        if flags_seen["business_tradeoff"] == 0:
            r.error("escalation rule: no inject forces a business tradeoff")
        if flags_seen["plan_silent"] == 0:
            r.error("escalation rule: no inject tests a point the plan is silent on")
        if pack["clocks"] and flags_seen["starts_clock"] == 0 and not pack.get("clock_start_inject"):
            r.error("no inject starts the notification clock")
        if pack.get("clock_start_inject") and pack["clock_start_inject"] not in inject_ids:
            r.error(f"clock_start_inject '{pack['clock_start_inject']}' is not an inject id")
        musts = pack.get("severity_musts") or {}
        for must in SEVERITY_MUSTS.get(severity, []):
            if not musts.get(must):
                r.warn(f"severity {severity} should include '{must}'; severity_musts.{must} is not set")

    # approval
    approval = pack.get("approval") or {}
    for key in APPROVAL_FIELDS:
        if key not in approval:
            r.error(f"approval block missing '{key}'")
    if approval.get("approved"):
        if approval.get("outline_hash") != approval_hash(pack):
            r.error("approval hash does not match the outline; the outline changed after approval, re-run ttx approve")
        if not approval.get("approved_by"):
            r.error("approved without approved_by")
    elif require_approval:
        r.error("outline is not approved; run ttx approve after the human review")

    # banner
    researched = [c["id"] for c in pack["clocks"] if c.get("tier") != "verified"]
    banner = pack.get("banner") or {}
    if researched and not banner.get("show"):
        r.error(f"researched-tier clocks {researched} present but banner.show is false")
    r.info = {
        "injects": len(injects),
        "findings_cited": sorted(cited),
        "researched_clocks": researched,
        "flags": flags_seen,
        "approved": bool(approval.get("approved")),
    }
    return r


_DEADLINE_RE = re.compile(r"\b(\d{1,4})\s*(hours?|hrs?|calendar days|business days|days)\b", re.IGNORECASE)


def _check_narrative_deadlines(inj: dict, clocks: list[dict], r: Result) -> None:
    """Flag deadline-shaped numbers in narrative that do not match any applicable clock."""
    allowed_hours = {float(c["deadline_hours"]) for c in clocks if c.get("deadline_hours") is not None}
    allowed_days = {float(c["deadline_hours"]) / 24.0 for c in clocks if c.get("deadline_hours") is not None}
    allowed_bdays = {float(c["deadline_business_days"]) for c in clocks if c.get("deadline_business_days") is not None}
    texts = [inj.get("what_happens", ""), inj.get("what_good_looks_like", ""), " ".join(inj.get("host_lines") or [])]
    for text in texts:
        for m in _DEADLINE_RE.finditer(text or ""):
            n = float(m.group(1))
            unit = m.group(2).lower()
            if unit.startswith("hour") or unit.startswith("hr"):
                ok = n in allowed_hours or n < 24  # short operational timings (e.g., "2 hours") are not regulatory clocks
            elif "business" in unit:
                ok = n in allowed_bdays
            else:
                ok = n in allowed_days or n <= 3
            if not ok:
                r.warn(f"inject {inj.get('id')}: narrative mentions '{m.group(0)}' which matches no applicable clock; cite the plan or remove it")


def check_approval(pack: dict) -> Result:
    r = Result("approval gate")
    approval = pack.get("approval") or {}
    if not approval.get("approved"):
        r.error("exercise pack is not approved; nothing is built before the human sign-off (ttx approve)")
    elif approval.get("outline_hash") != approval_hash(pack):
        r.error("exercise pack changed after approval; re-run ttx approve")
    return r
