"""Score engine.

Scores each tracker decision 1 to 3 on five dimensions:

  right_owner              the role that decided is the role the plan (or pack) names
  timely                   within the plan's internal commitment; for the inject that
                           starts the notification clocks, every applicable clock met
  escalation_notification  the parties expected at this inject were notified
  documented               the decision was recorded with enough detail to defend it
  followed_plan            the expected actions from the plan (or pack defaults) were taken

A dimension that does not apply to an inject is null and is left out of the
totals. Gap labels: plan gap (plan silent or unclear, cite the section),
people gap (plan says X at section y, team did Z), technical gap (the finding).

Same input, same score, every time: the result carries input hashes and no
timestamps.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .common import as_list, canonical_hash, parse_iso, sha256_file

DIMENSIONS = ["right_owner", "timely", "escalation_notification", "documented", "followed_plan"]
DIMENSION_LABELS = {
    "right_owner": "Right owner",
    "timely": "Timely",
    "escalation_notification": "Escalation and notification",
    "documented": "Documented",
    "followed_plan": "Followed the plan",
}
DECISION_COLUMNS = [
    "inject_id", "slide", "time_marker", "phase", "title", "expected_owner", "decision", "decided_by_role",
    "discussion_minutes", "scenario_minutes", "notified", "actions_completed", "plan_step_followed", "documented", "notes",
]
CLOCK_COLUMNS = [
    "clock_id", "name", "deadline_hours", "deadline_business_days", "tier", "owner_role",
    "planned_notify_hours", "internal_deadline_hours", "notes",
]
FIX_DAYS = {"technical_kev": 14, "people": 30, "technical": 45, "plan": 60}
RUBRIC = {
    "right_owner": {"3": "decided by the named owner (or an accepted delegate)", "2": "decided by another defined role", "1": "no owner recorded or an undefined role"},
    "timely": {"3": "within the plan commitment, or every clock met with an owner", "2": "within twice the commitment, or regulatory clocks met but an internal commitment or owner missed", "1": "slower than twice the commitment, no time recorded, or a regulatory clock missed or unplanned"},
    "escalation_notification": {"3": "every expected party notified", "2": "at least half notified", "1": "fewer than half notified"},
    "documented": {"3": "documented, with the decision written down", "2": "partly documented", "1": "not documented"},
    "followed_plan": {"3": "every expected action taken and the plan step followed", "2": "at least half the actions, or the step followed in part", "1": "fewer than half the actions, or the plan step not followed"},
}


# --------------------------------------------------------------------------- #
# Reading the tracker
# --------------------------------------------------------------------------- #

def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()
        return v if v else None
    return value


def _num(value: Any) -> float | None:
    value = _clean(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rows_from_sheet(ws) -> list[dict]:
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    out = []
    for r in rows[1:]:
        if r is None or all(c in (None, "") for c in r):
            continue
        out.append({header[i]: _clean(r[i]) for i in range(min(len(header), len(r))) if header[i]})
    return out


DECISION_INPUTS = ["decision", "decided_by_role", "discussion_minutes", "scenario_minutes", "notified",
                   "actions_completed", "plan_step_followed", "documented"]


def _recorded(row: dict) -> bool:
    """A prefilled row with every input cell empty means the inject was not reached."""
    return any(_clean(row.get(c)) not in (None, "") for c in DECISION_INPUTS)


def read_tracker(path: str | Path) -> dict:
    """Return {"decisions": {inject_id: row}, "clocks": {clock_id: row}}."""
    decisions, clocks = _read_tracker_raw(path)
    return {"decisions": {k: v for k, v in decisions.items() if _recorded(v)}, "clocks": clocks}


def _read_tracker_raw(path: str | Path) -> tuple[dict, dict]:
    p = Path(path)
    decisions: dict[str, dict] = {}
    clocks: dict[str, dict] = {}
    if p.suffix.lower() == ".xlsx":
        from openpyxl import load_workbook

        wb = load_workbook(p, data_only=True, read_only=True)
        if "Decisions" not in wb.sheetnames:
            raise ValueError(f"{p.name} has no 'Decisions' sheet; build the tracker with ttx build")
        for row in _rows_from_sheet(wb["Decisions"]):
            if row.get("inject_id"):
                decisions[str(row["inject_id"])] = row
        if "Clocks" in wb.sheetnames:
            for row in _rows_from_sheet(wb["Clocks"]):
                if row.get("clock_id"):
                    clocks[str(row["clock_id"])] = row
        wb.close()
    elif p.suffix.lower() == ".csv":
        with open(p, "r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                row = {k: _clean(v) for k, v in row.items() if k}
                if row.get("inject_id"):
                    decisions[str(row["inject_id"])] = row
        side = p.with_name(p.stem + "_clocks.csv")
        if side.exists():
            with open(side, "r", encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    row = {k: _clean(v) for k, v in row.items() if k}
                    if row.get("clock_id"):
                        clocks[str(row["clock_id"])] = row
    else:
        raise ValueError("tracker must be the .xlsx built by ttx build or a .csv decision log")
    return decisions, clocks


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _ids(value: Any) -> list[str]:
    return [str(x).strip() for x in as_list(value) if str(x).strip()]


def _org_items(pack: dict) -> dict[str, dict]:
    return {i["id"]: i for i in (pack.get("org_plan") or {}).get("items", [])}


def _role_names(pack: dict) -> dict[str, str]:
    return {r["id"]: r.get("name") or r["id"] for r in pack.get("roles", [])}


def _party_names(pack: dict) -> dict[str, str]:
    return {p["id"]: p.get("name") or p["id"] for p in pack.get("notify_parties", [])}


def _plan_owner_role(pack: dict) -> str:
    ids = [r["id"] for r in pack.get("roles", [])]
    for candidate in ("incident_commander", "ciso"):
        if candidate in ids:
            return candidate
    return ids[0] if ids else "incident_commander"


def _tech_owner_role(pack: dict) -> str:
    ids = [r["id"] for r in pack.get("roles", [])]
    for candidate in ("cio", "ciso", "incident_commander"):
        if candidate in ids:
            return candidate
    return ids[0] if ids else "cio"


def _cite(item: dict | None) -> str:
    if not item:
        return ""
    doc = item.get("document_title") or "Plan"
    sec = f" section {item['section']}" if item.get("section") else ""
    return f"{doc}{sec}"


def _exercise_date(pack: dict) -> date:
    raw = ((pack.get("intake") or {}).get("exercise") or {}).get("date")
    if raw:
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            pass
    return date.fromisoformat(str(pack.get("generated_at", "2026-01-01"))[:10])


def _action_item_id(action: dict) -> str | None:
    src = action.get("source") or ""
    if src.startswith("org_plan:"):
        return src.split(":", 1)[1]
    return None


def _ratio_score(hit: int, total: int) -> int:
    if total == 0:
        return 3
    if hit >= total:
        return 3
    if hit * 2 >= total:
        return 2
    return 1


# --------------------------------------------------------------------------- #
# Clocks
# --------------------------------------------------------------------------- #

def score_clocks(pack: dict, clock_rows: dict[str, dict], incident: dict | None = None) -> list[dict]:
    org_items = _org_items(pack)
    internal_by_clock: dict[str, dict] = {}
    for item in org_items.values():
        cid = item.get("applies_to_clock")
        if cid and item.get("internal_deadline_hours"):
            internal_by_clock[cid] = item
    trigger = parse_iso((incident or {}).get("trigger_at"))
    notified_at = (incident or {}).get("notifications") or {}

    def planned_for(cid: str) -> tuple[float | None, str]:
        row = clock_rows.get(cid, {})
        if trigger is not None and notified_at.get(cid):
            n = parse_iso(notified_at[cid])
            return round((n - trigger).total_seconds() / 3600.0, 2), "incident timestamps"
        return _num(row.get("planned_notify_hours")), "tracker planned_notify_hours"

    results = []
    for clock in pack.get("clocks", []):
        cid = clock["id"]
        row = clock_rows.get(cid, {})
        owner = _clean(row.get("owner_role"))
        planned, basis = planned_for(cid)
        deadline = clock.get("deadline_hours")
        approx = False
        if deadline is None and clock.get("deadline_business_days") is not None:
            # calendar-hour equivalent of N business days (weekends only; holidays not modeled)
            deadline = round(float(clock["deadline_business_days"]) * 24 * 7 / 5, 2)
            approx = True
        parent = clock.get("after_clock")
        if parent and deadline is not None:
            # chained clock: the limit runs from the parent clock's planned notification
            parent_planned, _ = planned_for(parent)
            deadline = None if parent_planned is None else round(parent_planned + float(deadline), 2)
        res: dict[str, Any] = {
            "clock_id": cid,
            "name": clock.get("name"),
            "regulator": clock.get("regulator"),
            "deadline_text": clock.get("deadline_text"),
            "deadline_hours": deadline,
            "deadline_is_business_day_approximation": approx,
            "tier": clock.get("tier"),
            "verified_date": clock.get("verified_date"),
            "source_url": clock.get("source_url"),
            "citation": clock.get("citation"),
            "owner_role": owner,
            "planned_notify_hours": planned,
            "basis": basis,
            "after_clock": parent,
        }
        if parent and deadline is None and clock.get("deadline_hours") is not None:
            res.update({"status": "not_planned", "met": False, "margin_hours": None,
                        "note": f"runs from the notification under {parent}, which was not planned"})
        elif deadline is None:
            res.update({"status": "no_fixed_deadline", "met": None, "margin_hours": None})
        elif planned is None:
            res.update({"status": "not_planned", "met": False, "margin_hours": None})
        else:
            margin = round(float(deadline) - planned, 2)
            res.update({"status": "met" if margin >= 0 else "missed", "met": margin >= 0, "margin_hours": margin})
        internal = internal_by_clock.get(cid)
        if internal:
            ih = float(internal["internal_deadline_hours"])
            res["internal_deadline_hours"] = ih
            res["internal_source"] = internal["id"]
            res["internal_quote"] = internal.get("quote")
            res["internal_section"] = internal.get("section")
            res["internal_met"] = (planned is not None and planned <= ih)
            res["internal_margin_hours"] = round(ih - planned, 2) if planned is not None else None
        results.append(res)
    return results


# --------------------------------------------------------------------------- #
# Injects
# --------------------------------------------------------------------------- #

def score_inject(inj: dict, row: dict | None, pack: dict, clock_results: list[dict]) -> dict:
    role_names = _role_names(pack)
    org_items = _org_items(pack)
    out: dict[str, Any] = {
        "inject_id": inj["id"],
        "title": inj.get("title"),
        "phase": inj.get("phase"),
        "slide_number": inj.get("slide_number"),
        "procedure": inj.get("procedure_tested"),
        "reached": row is not None,
        "scores": {d: None for d in DIMENSIONS},
        "reasons": {},
        "decision": None,
        "decided_by_role": None,
        "actions_expected": [a["id"] for a in inj.get("expected_actions", [])],
        "actions_completed": [],
        "actions_missed": [],
        "notifications_expected": list(inj.get("expected_notifications") or []),
        "notifications_made": [],
        "notifications_missed": [],
    }
    if row is None:
        out["reasons"]["all"] = "inject not reached or not recorded"
        return out
    decision = _clean(row.get("decision"))
    owner = _clean(row.get("decided_by_role"))
    out["decision"] = decision
    out["decided_by_role"] = owner
    scores, reasons = out["scores"], out["reasons"]

    # right owner
    expected = inj.get("decision_owner_role")
    acceptable = set(inj.get("acceptable_owner_roles") or [])
    if not owner:
        scores["right_owner"], reasons["right_owner"] = 1, "no deciding role recorded"
    elif owner == expected or owner in acceptable:
        scores["right_owner"], reasons["right_owner"] = 3, f"decided by {role_names.get(owner, owner)}"
    elif owner in role_names:
        scores["right_owner"], reasons["right_owner"] = 2, f"decided by {role_names.get(owner, owner)}; expected {role_names.get(expected, expected)}"
    else:
        scores["right_owner"], reasons["right_owner"] = 1, f"decided by '{owner}', which is not a defined role"

    # timely
    starts = as_list((inj.get("flags") or {}).get("starts_clock"))
    if starts:
        mine = [c for c in clock_results if c["clock_id"] in starts]
        numeric = [c for c in mine if c["status"] != "no_fixed_deadline"]
        reg_missed = [c for c in numeric if c["status"] in {"missed", "not_planned"}]
        internal_missed = [c for c in mine if c.get("internal_met") is False]
        unowned = [c for c in mine if not c.get("owner_role")]
        if reg_missed:
            scores["timely"] = 1
            reasons["timely"] = "regulatory clock missed or unplanned: " + ", ".join(c["clock_id"] for c in reg_missed)
        elif internal_missed or unowned:
            scores["timely"] = 2
            parts = []
            if internal_missed:
                parts.append("internal commitment missed: " + ", ".join(c["clock_id"] for c in internal_missed))
            if unowned:
                parts.append("no owner named: " + ", ".join(c["clock_id"] for c in unowned))
            reasons["timely"] = "; ".join(parts)
        else:
            scores["timely"], reasons["timely"] = 3, "every applicable clock met with an owner named"
    else:
        commitment = inj.get("plan_commitment_minutes")
        scen = _num(row.get("scenario_minutes"))
        disc = _num(row.get("discussion_minutes"))
        if commitment:
            m = scen if scen is not None else disc
            if m is None:
                scores["timely"], reasons["timely"] = 1, f"no time recorded against the {int(commitment)}-minute commitment"
            elif m <= commitment:
                scores["timely"], reasons["timely"] = 3, f"{m:g} minutes against a {int(commitment)}-minute commitment"
            elif m <= 2 * commitment:
                scores["timely"], reasons["timely"] = 2, f"{m:g} minutes against a {int(commitment)}-minute commitment"
            else:
                scores["timely"], reasons["timely"] = 1, f"{m:g} minutes against a {int(commitment)}-minute commitment"
        else:
            budget = inj.get("time_budget_minutes") or 10
            m = disc if disc is not None else scen
            if m is None:
                scores["timely"], reasons["timely"] = 1, "no time recorded"
            elif m <= budget:
                scores["timely"], reasons["timely"] = 3, f"{m:g} minutes of a {budget}-minute budget (no plan commitment)"
            elif m <= 1.5 * budget:
                scores["timely"], reasons["timely"] = 2, f"{m:g} minutes of a {budget}-minute budget (no plan commitment)"
            else:
                scores["timely"], reasons["timely"] = 1, f"{m:g} minutes of a {budget}-minute budget (no plan commitment)"

    # escalation and notification
    exp_n = list(inj.get("expected_notifications") or [])
    got = _ids(row.get("notified"))
    out["notifications_made"] = got
    if exp_n:
        hit = [n for n in exp_n if n in got]
        out["notifications_missed"] = [n for n in exp_n if n not in got]
        scores["escalation_notification"] = _ratio_score(len(hit), len(exp_n))
        reasons["escalation_notification"] = f"{len(hit)} of {len(exp_n)} expected parties notified"
    else:
        reasons["escalation_notification"] = "no notifications expected at this inject"

    # documented
    doc = (_clean(row.get("documented")) or "").lower()
    if doc in {"yes", "y", "true"} and decision:
        scores["documented"], reasons["documented"] = 3, "decision recorded and documented"
    elif doc in {"yes", "y", "true", "partial", "partly"}:
        scores["documented"], reasons["documented"] = 2, "partly documented"
    else:
        scores["documented"], reasons["documented"] = 1, "not documented"

    # followed the plan
    expected_actions = inj.get("expected_actions") or []
    done = set(_ids(row.get("actions_completed")))
    out["actions_completed"] = [a["id"] for a in expected_actions if a["id"] in done]
    out["actions_missed"] = [a["id"] for a in expected_actions if a["id"] not in done]
    step = (_clean(row.get("plan_step_followed")) or "").lower().replace(" ", "_")
    out["plan_step_followed"] = step or None
    proc_type = (inj.get("procedure_tested") or {}).get("type")
    if proc_type == "plan_silent":
        reasons["followed_plan"] = "the plan is silent on this decision; scored as a plan gap instead"
    else:
        s = _ratio_score(len(out["actions_completed"]), len(expected_actions))
        why = f"{len(out['actions_completed'])} of {len(expected_actions)} expected actions"
        if step in {"no", "n", "deviated"}:
            s, why = 1, why + "; plan step not followed"
        elif step in {"partial", "partly", "plan_unclear"}:
            s, why = min(s, 2), why + ("; plan step followed in part" if step != "plan_unclear" else "; team found the plan unclear")
        scores["followed_plan"], reasons["followed_plan"] = s, why

    applicable = [v for v in scores.values() if v is not None]
    out["total"] = sum(applicable)
    out["max"] = 3 * len(applicable)
    return out


# --------------------------------------------------------------------------- #
# Gaps and coverage
# --------------------------------------------------------------------------- #

def _gaps(pack: dict, inject_results: list[dict], clock_results: list[dict]) -> list[dict]:
    org_items = _org_items(pack)
    role_names = _role_names(pack)
    party_names = _party_names(pack)
    ex_date = _exercise_date(pack)
    plan_owner = _plan_owner_role(pack)
    gaps: list[dict] = []
    injects = {j["id"]: j for j in pack.get("injects", [])}
    org_gaps = {g["id"]: g for g in (pack.get("org_plan") or {}).get("gaps", [])}

    def add(label, inject_id, finding, citation, fix, owner, days, **extra):
        gaps.append({
            "id": f"GAP{len(gaps) + 1}",
            "label": label,
            "inject_id": inject_id,
            "finding": finding,
            "citation": citation,
            "fix": fix,
            "owner_role": owner,
            "owner": role_names.get(owner, owner),
            "due": (ex_date + timedelta(days=days)).isoformat(),
            **extra,
        })

    for res in inject_results:
        inj = injects[res["inject_id"]]
        proc = inj.get("procedure_tested") or {}
        proc_item = org_items.get(proc.get("ref")) if proc.get("type") == "org_plan" else None
        if not res["reached"]:
            continue
        decided = role_names.get(res["decided_by_role"], res["decided_by_role"] or "no one")
        # plan gaps
        if proc.get("type") == "plan_silent":
            g = org_gaps.get(proc.get("ref")) or {}
            topic = g.get("topic") or proc.get("label") or "this decision"
            outcome = f"The team decided: {res['decision']}" if res["decision"] else "The team reached no decision"
            add("plan", inj["id"], f"The plan is silent on {topic.lower()}. {outcome} ({decided}).",
                f"{proc.get('ref') or 'no plan section'}: {g.get('note') or proc.get('label')}",
                f"Add a section that names who decides {topic.lower()}, who must be consulted, and how the decision is recorded.",
                plan_owner, FIX_DAYS["plan"])
        if res.get("plan_step_followed") == "plan_unclear" and proc_item:
            add("plan", inj["id"], f"The team found {_cite(proc_item)} unclear when applying it to this inject.",
                f"{_cite(proc_item)}: \"{proc_item.get('quote')}\"",
                f"Rewrite {_cite(proc_item)} so the decision, the owner, and the timing are explicit.",
                plan_owner, FIX_DAYS["plan"])
        # people gaps: owner
        if res["scores"]["right_owner"] in (1, 2):
            exp = inj.get("decision_owner_role")
            if proc_item and proc_item.get("category") in {"decision_authority", "role", "comms_template"}:
                cite = f"{_cite(proc_item)}: \"{proc_item.get('quote')}\""
                says = f"{_cite(proc_item)} names {role_names.get(exp, exp)}"
            else:
                cite = f"{pack.get('pack_display_name') or pack.get('pack')} pack default role"
                says = f"the expected owner is {role_names.get(exp, exp)}"
            add("people", inj["id"], f"{says}; the decision was made by {decided}.", cite,
                f"Brief {role_names.get(exp, exp)} and their delegate on this authority and rehearse the hand-off.",
                exp, FIX_DAYS["people"])
        # people gaps: missed plan actions
        for aid in res["actions_missed"]:
            action = next(a for a in inj.get("expected_actions", []) if a["id"] == aid)
            item = org_items.get(_action_item_id(action) or "")
            if item:
                add("people", inj["id"], f"Not done at this inject: {item.get('label')} ({_cite(item)}: {action['text']}).",
                    f"{_cite(item)}: \"{item.get('quote')}\"",
                    f"Train the roles named in {_cite(item)} on this step and add it to the incident checklist.",
                    inj.get("decision_owner_role"), FIX_DAYS["people"], action_id=aid)
            else:
                add("people", inj["id"], f"Expected action not taken: {action['text']}.",
                    f"{action.get('source')}", "Add this step to the incident checklist and the next exercise.",
                    inj.get("decision_owner_role"), FIX_DAYS["people"], action_id=aid)
        # people gaps: notifications
        if res["notifications_missed"]:
            names = ", ".join(party_names.get(n, n) for n in res["notifications_missed"])
            add("people", inj["id"], f"Not notified at this inject: {names}.",
                "expected notifications for this inject (exercise pack)",
                "Add these parties, with a named caller and a backup, to the notification list for this severity.",
                inj.get("decision_owner_role"), FIX_DAYS["people"])
        # people gaps: plan timing
        if res["scores"]["timely"] in (1, 2) and not as_list((inj.get("flags") or {}).get("starts_clock")) and inj.get("plan_commitment_minutes"):
            timed = [org_items.get(_action_item_id(a) or "") for a in inj.get("expected_actions", [])]
            timed = [t for t in timed if t and t.get("timing_minutes") == inj.get("plan_commitment_minutes")]
            item = timed[0] if timed else proc_item
            add("people", inj["id"], f"Slower than the plan's commitment: {res['reasons']['timely']}.",
                f"{_cite(item)}: \"{item.get('quote')}\"" if item else "plan timing commitment",
                "Rehearse this escalation step against the clock; confirm the on-call path reaches the named role in time.",
                inj.get("decision_owner_role"), FIX_DAYS["people"])

    # clocks
    starter = next((j["id"] for j in pack.get("injects", []) if as_list((j.get("flags") or {}).get("starts_clock"))), None)
    for c in clock_results:
        if c["status"] == "missed":
            add("people", starter, f"{c['name']}: planned at {c['planned_notify_hours']:g} hours against a {c['deadline_hours']:g}-hour limit, missed by {abs(c['margin_hours']):g} hours.",
                f"{c['citation']} ({c['tier']} tier; source on the evidence page)",
                "Name the owner for this clock in the plan, pre-draft the notice, and put the deadline in the incident checklist.",
                c.get("owner_role") or _plan_owner_role(pack), FIX_DAYS["people"], clock_id=c["clock_id"])
        elif c["status"] == "not_planned":
            add("plan", starter, f"{c['name']} applies but the team did not plan a notification time{'' if c.get('owner_role') else ' or name an owner'}.",
                f"{c['citation']} ({c['tier']} tier; source on the evidence page)",
                "Add this obligation, its owner, and its deadline to the notification section of the plan.",
                _plan_owner_role(pack), FIX_DAYS["plan"], clock_id=c["clock_id"])
        if c.get("internal_met") is False and c["status"] == "met":
            item = org_items.get(c.get("internal_source"))
            add("people", starter, f"{c['name']}: planned at {c['planned_notify_hours']:g} hours, inside the regulatory limit but outside the plan's own {c['internal_deadline_hours']:g}-hour standard.",
                f"{_cite(item)}: \"{c.get('internal_quote')}\"",
                "Hold the team to the plan's internal standard, or change the plan if the standard is not realistic.",
                c.get("owner_role") or _plan_owner_role(pack), FIX_DAYS["people"], clock_id=c["clock_id"])

    # technical gaps: every finding on the exercised path
    seed = pack.get("seed") or {}
    tech_owner = _tech_owner_role(pack)
    for part in ("entry", "pivot", "target"):
        node = seed.get(part) or {}
        if not node.get("finding_id"):
            continue
        kev = node.get("kev")
        cve = node.get("cve") or "no CVE"
        desc = node.get("plugin_name") or node.get("technique") or "open finding"
        add("technical", None,
            f"Finding {node['finding_id']} on {node.get('asset')} ({desc}, {cve}{', CISA KEV' if kev else ''}{', VPR ' + str(node.get('vpr')) if node.get('vpr') is not None else ''}) is open and was the {part} step of the exercised path.",
            f"seed {part}: {node['finding_id']} (rule {node.get('rule')}, source {seed.get('source')})",
            f"Remediate or mitigate {node['finding_id']} on {node.get('asset')}, verify closure in the next scan, and rerun this path next quarter if it is still open.",
            tech_owner, FIX_DAYS["technical_kev"] if kev else FIX_DAYS["technical"], finding_id=node["finding_id"])
    return gaps


def _coverage(pack: dict, inject_results: list[dict]) -> dict:
    org_items = _org_items(pack)
    if not org_items:
        return {"present": False, "rows": [], "counts": {}, "note": "No plan was uploaded; the exercise used pack defaults."}
    by_item: dict[str, dict] = {iid: {"item_id": iid, "section": it.get("section"), "label": it.get("label"),
                                      "category": it.get("category"), "status": "not_covered", "injects": [], "evidence": []}
                                for iid, it in org_items.items()}
    results = {r["inject_id"]: r for r in inject_results}
    for inj in pack.get("injects", []):
        res = results.get(inj["id"])
        proc = inj.get("procedure_tested") or {}
        refs: list[tuple[str, str | None]] = []
        if proc.get("type") == "org_plan" and proc.get("ref") in by_item:
            refs.append((proc["ref"], None))
        for a in inj.get("expected_actions", []):
            iid = _action_item_id(a)
            if iid in by_item:
                refs.append((iid, a["id"]))
        for iid, aid in refs:
            row = by_item[iid]
            row["injects"].append(inj["id"])
            if res is None or not res["reached"]:
                status = "not_reached"
            elif aid is not None:
                status = "followed" if aid in res["actions_completed"] else "deviated"
            else:
                step = res.get("plan_step_followed")
                status = "deviated" if step in {"no", "n", "deviated", "partial", "partly", "plan_unclear"} else "followed"
            row["evidence"].append({"inject": inj["id"], "status": status})
    order = {"deviated": 0, "followed": 1, "not_reached": 2, "not_covered": 3}
    for row in by_item.values():
        if row["evidence"]:
            statuses = {e["status"] for e in row["evidence"]}
            if "deviated" in statuses:
                row["status"] = "deviated"
            elif "followed" in statuses:
                row["status"] = "followed"
            else:
                row["status"] = "not_reached"
        row["injects"] = sorted(set(row["injects"]), key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)
    silent = []
    tested_gaps = {(j.get("procedure_tested") or {}).get("ref") for j in pack.get("injects", []) if (j.get("procedure_tested") or {}).get("type") == "plan_silent"}
    for g in (pack.get("org_plan") or {}).get("gaps", []):
        silent.append({"gap_id": g["id"], "topic": g.get("topic"), "note": g.get("note"),
                       "status": "silent_exercised" if g["id"] in tested_gaps else "silent_not_exercised"})
    rows = sorted(by_item.values(), key=lambda r: (_section_key(r["section"]), r["item_id"]))
    counts = {k: sum(1 for r in rows if r["status"] == k) for k in ("followed", "deviated", "not_reached", "not_covered")}
    counts["silent_exercised"] = sum(1 for s in silent if s["status"] == "silent_exercised")
    counts["silent_not_exercised"] = sum(1 for s in silent if s["status"] == "silent_not_exercised")
    sections = {}
    for r in rows:
        key = str(r["section"] or "unsectioned")
        sec = sections.setdefault(key, {"section": key, "items": 0, "followed": 0, "deviated": 0, "not_reached": 0, "not_covered": 0})
        sec["items"] += 1
        sec[r["status"]] += 1
    return {"present": True, "rows": rows, "silent": silent, "counts": counts,
            "sections": sorted(sections.values(), key=lambda s: _section_key(s["section"]))}


def _section_key(section: Any) -> tuple:
    parts = []
    for p in str(section or "999").split("."):
        parts.append(int(p) if p.isdigit() else 999)
    return tuple(parts)


# --------------------------------------------------------------------------- #
# Top level
# --------------------------------------------------------------------------- #

def _headline(pack: dict, summary: dict, clock_results: list[dict], gaps: list[dict]) -> str:
    org = (pack.get("organization") or {}).get("short_name") or (pack.get("organization") or {}).get("name") or "The team"
    avgs = {k: v for k, v in summary["dimension_averages"].items() if v is not None}
    best = max(avgs, key=lambda k: (avgs[k], -DIMENSIONS.index(k))) if avgs else None
    worst = min(avgs, key=lambda k: (avgs[k], DIMENSIONS.index(k))) if avgs else None
    missed = sorted([c for c in clock_results if c["status"] == "missed"], key=lambda c: c["margin_hours"])
    unplanned = [c for c in clock_results if c["status"] == "not_planned"]
    if missed:
        c = missed[0]
        clock_line = f"{c['name']} missed by {abs(c['margin_hours']):g} hours"
    elif unplanned:
        clock_line = f"{unplanned[0]['name']} had no plan or owner"
    elif clock_results:
        clock_line = "every notification clock met"
    else:
        clock_line = "no notification clocks applied"
    counts = {lab: sum(1 for g in gaps if g["label"] == lab) for lab in ("plan", "people", "technical")}
    parts = [f"{org} scored {summary['percent']}% across {summary['injects_scored']} decisions"]
    if best and worst and best != worst:
        parts.append(f"strongest on {DIMENSION_LABELS[best].lower()}, weakest on {DIMENSION_LABELS[worst].lower()}")
    parts.append(clock_line)
    head = "; ".join(parts) + "."
    return head + f" {counts['plan']} plan, {counts['people']} people, and {counts['technical']} technical gaps."


def score_tracker(pack: dict, tracker_path: str | Path, incident_file: str | Path | None = None) -> dict:
    from .common import read_json

    tracker = read_tracker(tracker_path)
    incident = read_json(incident_file) if incident_file else None
    clock_results = score_clocks(pack, tracker["clocks"], incident)
    inject_results = [score_inject(inj, tracker["decisions"].get(inj["id"]), pack, clock_results) for inj in pack.get("injects", [])]

    dim_avgs: dict[str, float | None] = {}
    for d in DIMENSIONS:
        vals = [r["scores"][d] for r in inject_results if r["scores"][d] is not None]
        dim_avgs[d] = round(sum(vals) / len(vals), 2) if vals else None
    total = sum(r.get("total", 0) for r in inject_results)
    maximum = sum(r.get("max", 0) for r in inject_results)
    scored = sum(1 for r in inject_results if r["reached"])
    summary = {
        "total_score": total,
        "max_score": maximum,
        "percent": round(100.0 * total / maximum, 1) if maximum else 0.0,
        "injects_scored": scored,
        "injects_total": len(inject_results),
        "dimension_averages": dim_avgs,
        "clocks_met": sum(1 for c in clock_results if c["status"] == "met"),
        "clocks_missed": sum(1 for c in clock_results if c["status"] == "missed"),
        "clocks_not_planned": sum(1 for c in clock_results if c["status"] == "not_planned"),
        "clocks_no_fixed_deadline": sum(1 for c in clock_results if c["status"] == "no_fixed_deadline"),
    }
    gaps = _gaps(pack, inject_results, clock_results)
    coverage = _coverage(pack, inject_results)
    result = {
        "schema_version": "1",
        "inputs": {
            "exercise_pack_hash": canonical_hash({k: v for k, v in pack.items() if k != "approval"}),
            "approval_hash": (pack.get("approval") or {}).get("outline_hash"),
            "tracker_file": Path(tracker_path).name,
            "tracker_sha256": sha256_file(tracker_path),
            "incident_file": Path(incident_file).name if incident_file else None,
        },
        "rubric": RUBRIC,
        "dimension_labels": DIMENSION_LABELS,
        "summary": summary,
        "injects": inject_results,
        "clocks": clock_results,
        "gaps": gaps,
        "coverage": coverage,
        "plan_source": "org_plan" if (pack.get("org_plan") or {}).get("items") else "pack_defaults",
    }
    result["headline"] = _headline(pack, summary, clock_results, gaps)
    return result
