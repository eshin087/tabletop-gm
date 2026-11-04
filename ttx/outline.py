"""Deterministic scenario outline skeleton.

Builds a draft exercise_pack.json from the seed, the clocks, the industry pack,
and the org plan. Every inject slot is pre-filled with the facts the engine
knows (the asset names, the finding IDs, the clock that starts, the plan item
it tests, the expected actions with their sources) and with plain template
prose the scenario_design skill rewrites. The model may change wording; it may
not add a system name, a deadline, or a policy claim that is not already here.

Running this without a model produces a complete, valid, buildable outline.
"""

from __future__ import annotations

from typing import Any

from .clock_engine import BANNER_TEXT, _sort_hours
from .common import as_list, now_iso, slugify
from .packs import load_pack
from .validators import approval_hash

SLOT_PLANS: dict[int, list[str]] = {
    30: ["escalation", "tradeoff", "notification"],
    60: ["detection", "escalation", "containment", "tradeoff", "notification"],
    90: ["detection", "escalation", "containment", "tradeoff", "recovery", "notification", "public"],
}
# minutes kept for the welcome and the hot wash; the rest is split across the injects
OVERHEAD_MINUTES = {30: 8, 60: 15, 90: 20}
PHASE_OF_SLOT = {
    "detection": "detection", "second_signal": "detection", "escalation": "escalation", "severity": "escalation",
    "containment": "containment", "conflict": "containment", "tradeoff": "containment", "recovery": "recovery",
    "notification": "notification", "public": "notification",
}
SLOT_CATEGORIES = {
    "detection": ["escalation_step", "severity_level"],
    "second_signal": ["severity_level", "escalation_step"],
    "escalation": ["playbook_step", "decision_authority", "escalation_step"],
    "severity": ["severity_level", "decision_authority"],
    "containment": ["decision_authority", "containment_procedure", "playbook_step"],
    "conflict": ["containment_procedure", "playbook_step"],
    "tradeoff": ["decision_authority", "containment_procedure"],
    "recovery": ["recovery_objective", "playbook_step"],
    "notification": ["notification_procedure", "decision_authority"],
    "public": ["comms_template", "decision_authority"],
}
# keywords that pick the best plan item within a category for each slot
SLOT_KEYWORDS = {
    "detection": ["security operations notifies", "15 minutes", "identifying"],
    "second_signal": ["sev2", "privileged"],
    "escalation": ["declares a sev1", "declar"],
    "severity": ["raise or lower", "assigns the severity"],
    "containment": ["shutdown or isolation", "isolation", "isolate"],
    "conflict": ["forensic image", "evidence", "preserve"],
    "tradeoff": ["ransom", "shutdown", "diversion"],
    "recovery": ["restored in this order", "restore order", "recovery time"],
    "notification": ["owns the regulatory", "notification ownership", "regulatory", "individual notification"],
    "public": ["holding statement", "external statement", "media"],
}
# phases whose plan items make good expected actions for each slot
SLOT_ACTION_PHASES = {
    "detection": ["detection"],
    "second_signal": ["detection", "escalation"],
    "escalation": ["escalation"],
    "severity": ["escalation"],
    "containment": ["containment"],
    "conflict": ["containment"],
    "tradeoff": ["containment", "escalation"],
    "recovery": ["recovery"],
    "notification": ["notification"],
    "public": ["notification"],
}
SLOT_ACCEPTABLE_OWNERS = {
    "containment": ["incident_commander"],
    "detection": ["incident_commander"],
    "public": ["communications"],
}
SLOT_OWNER_KEYS = {
    "detection": ["security_operations", "ciso", "incident_commander"],
    "second_signal": ["ciso", "incident_commander"],
    "escalation": ["incident_commander", "ciso"],
    "severity": ["ciso", "incident_commander"],
    "containment": ["cio", "incident_commander", "ciso"],
    "conflict": ["incident_commander", "ciso"],
    "tradeoff": ["ceo", "incident_commander", "coo"],
    "recovery": ["cio", "incident_commander"],
    "notification": ["general_counsel", "privacy_officer", "compliance_officer", "legal"],
    "public": ["ceo", "communications", "comms"],
}
SLOT_NOTIFY = {
    "detection": [],
    "second_signal": ["executive_leadership"],
    "escalation": ["executive_leadership", "legal_counsel", "cyber_insurer"],
    "severity": ["executive_leadership", "legal_counsel"],
    "containment": ["executive_leadership"],
    "conflict": ["legal_counsel"],
    "tradeoff": ["executive_leadership"],
    "recovery": ["executive_leadership"],
    "notification": ["primary_regulator", "primary_federal_regulator", "hhs_ocr", "state_health_department", "fbi", "cyber_insurer", "customers", "patients"],
    "public": ["executive_leadership", "legal_counsel"],
}
SLOT_FLAGS = {
    "conflict": {"conflicting_information": True},
    "tradeoff": {"business_tradeoff": True},
    "recovery": {"business_tradeoff": True},
}
GROUND_RULES = [
    "This is a discussion, not a test of individuals. There are no wrong answers, only decisions and their consequences.",
    "Respond as you would today with the plans, people, and tools you actually have, not the ones you wish you had.",
    "The facilitator controls the clock. When the facilitator says time has passed, it has.",
    "Decisions are recorded as the team states them. Say who decided and who was told.",
    "Nothing discussed here is a finding against any person. The after-action report labels gaps in plans, roles, and technology.",
    "Phones down unless you are playing the role of the person being called.",
]
OBJECTIVES = [
    "Exercise the organization's own written procedures under a scenario built from its own exposure data.",
    "Confirm who holds each decision and whether the escalation path works at speed.",
    "Test the notification clocks that apply to this organization and who owns each one.",
    "Find the points where the plan is silent, contradictory, or unknown to the people who must use it.",
    "Produce a scored after-action report with owners and dates for every gap.",
]
HOT_WASH = [
    "What was the first moment you knew this was serious, and who did you tell?",
    "Which decision took longest, and what information would have made it faster?",
    "Where did the plan help, where did it get in the way, and where was it silent?",
    "Which notification clock worried you most, and who owns it on a Saturday?",
    "What one change would you make before the next real incident?",
]


def _phase_marker(order: int, start_min: int) -> str:
    return f"T+{start_min // 60}:{start_min % 60:02d}"


def _pick_role(roles: list[dict], keys: list[str]) -> str:
    ids = [r["id"] for r in roles]
    for k in keys:
        if k in ids:
            return k
    for k in keys:
        for rid in ids:
            if k in rid:
                return rid
    return ids[0] if ids else "incident_commander"


def _item_text(item: dict) -> str:
    return " ".join(str(item.get(k) or "") for k in ("label", "value", "quote")).lower()


def _find_plan_item(items: list[dict], categories: list[str], used: set[str], keywords: list[str]) -> dict | None:
    """Best unused item: keyword match within the preferred categories, then any unused item in them."""
    for kw in keywords:
        for cat in categories:
            for item in items:
                if item.get("category") == cat and item.get("id") not in used and kw in _item_text(item):
                    return item
    for cat in categories:
        for item in items:
            if item.get("category") == cat and item.get("id") not in used:
                return item
    return None


ACTIONABLE = {"playbook_step", "escalation_step", "notification_procedure", "containment_procedure", "recovery_objective"}


def _action_from_item(item: dict) -> dict:
    return {"id": item["id"], "text": item.get("value") or item.get("label"), "source": f"org_plan:{item['id']}",
            "timing_minutes": item.get("timing_minutes")}


SLOT_ACTION_CATEGORIES = {"public": ["comms_template"]}


def _plan_actions(items: list[dict], phases: list[str], used: set[str], keywords: list[str], limit: int = 3,
                  prefer: list[str] | None = None) -> list[dict]:
    prefer = prefer or []
    pool = [i for i in items if i["id"] not in used and (
        (i.get("phase") in phases and i.get("category") in ACTIONABLE) or i.get("category") in prefer)]
    pool.sort(key=lambda i: (0 if i.get("category") in prefer else 1,
                             0 if any(k in _item_text(i) for k in keywords) else 1,
                             phases.index(i["phase"]) if i.get("phase") in phases else len(phases)))
    out = []
    for item in pool[:max(limit, 0)]:
        out.append(_action_from_item(item))
        used.add(item["id"])
    return out


def _pack_actions(pack, phase: str, limit: int = 3) -> list[dict]:
    out = []
    for a in (pack.expected_actions.get(phase) or [])[:limit]:
        out.append({"id": a["id"], "text": a["text"], "source": f"pack_default:{pack.slug}:{a['id']}"})
    return out


def _fmt(template: str, ctx: dict) -> str:
    try:
        return template.format(**ctx)
    except (KeyError, IndexError):
        return template


def build_outline(intake: dict, seed: dict, clocks: dict, org_plan: dict | None = None, packs_base=None) -> dict:
    pack = load_pack(str(intake.get("industry")), packs_base)
    duration = int(intake.get("duration_minutes") or 90)
    if duration not in SLOT_PLANS:
        raise ValueError(f"duration_minutes must be one of {sorted(SLOT_PLANS)}")
    severity = int(intake.get("severity_level") or 3)
    org = intake.get("organization") or {}
    org_name = org.get("name") or "the organization"
    family = str(intake.get("scenario_family") or ("ransomware" if severity >= 3 else "business email compromise"))
    plan_items = list((org_plan or {}).get("items") or [])
    plan_present = bool(plan_items)

    # roles: org plan roles first, pack defaults fill the rest
    roles: list[dict] = []
    seen_roles: set[str] = set()
    for item in plan_items:
        if item.get("category") == "role":
            rid = item.get("role_id") or slugify(item.get("label", ""))
            if rid in seen_roles:
                continue
            roles.append({"id": rid, "name": item.get("label"), "authority": item.get("value"), "source": f"org_plan:{item['id']}"})
            seen_roles.add(rid)
    for role in pack.roles:
        if role["id"] not in seen_roles:
            roles.append({"id": role["id"], "name": role["name"], "authority": ", ".join(role.get("decides") or []), "source": f"pack_default:{pack.slug}"})
            seen_roles.add(role["id"])

    entry, pivot, target = seed["entry"], seed["pivot"], seed["target"]
    applicable, out_of_scenario = scenario_clocks(clocks.get("clocks") or [], target.get("data") or as_list(intake.get("data_types")))
    clock_ids = [c["id"] for c in applicable]
    tight = sorted([c for c in applicable if (c.get("deadline_hours") is not None or c.get("deadline_business_days") is not None)
                    and not c.get("after_clock")], key=lambda c: (_sort_hours(c), c["id"]))
    tight_clock = tight[0] if tight else None
    data_list = list(target.get("data") or as_list(intake.get("data_types")))
    ctx = {
        "org": org_name,
        "entry_asset": entry.get("asset"),
        "entry_cve": entry.get("cve") or "a publicly known vulnerability",
        "entry_finding": entry.get("finding_id") or entry.get("assumption"),
        "pivot_asset": pivot.get("asset"),
        "pivot_desc": (f"the identity server {pivot.get('asset')}" if str(pivot.get("rule", "")).startswith("identity_tier")
                       else f"the high-criticality server {pivot.get('asset')}" if pivot.get("rule") == "high_acr_server"
                       else str(pivot.get("asset"))),
        "pivot_technique": pivot.get("technique"),
        "target_asset": target.get("asset"),
        "data_types": _and_join(data_list),
        "family": family,
        "tight_clock": (tight_clock.get("regulator") or tight_clock["name"]) if tight_clock else "the regulator",
        "tight_deadline": _deadline_words(tight_clock) if tight_clock else "the deadline in the plan",
    }

    slots = SLOT_PLANS[duration]
    overhead = OVERHEAD_MINUTES[duration]
    per_inject = (duration - overhead) // len(slots)
    used_items: set[str] = set()
    injects: list[dict] = []
    slide = 6
    source_cycle = {
        "detection": ("entry", entry), "second_signal": ("entry", entry), "escalation": ("entry", entry),
        "severity": ("pivot", pivot), "containment": ("pivot", pivot), "conflict": ("pivot", pivot),
        "tradeoff": ("target", target), "recovery": ("target", target), "notification": ("target", target), "public": ("target", target),
    }
    plan_silent_done = False
    used_actions: set[str] = set()
    used_pack_actions: set[str] = set()
    for i, slot in enumerate(slots, start=1):
        phase = PHASE_OF_SLOT[slot]
        start_min = overhead // 2 + (i - 1) * per_inject
        part_name, part = source_cycle[slot]
        if part.get("finding_id"):
            source = {"type": "finding", "ref": part["finding_id"], "note": f"{part_name} finding on {part.get('asset')}"}
        else:
            source = {"type": "assumption", "ref": part.get("assumption") or seed["assumptions"][0]["id"], "note": f"{part_name} is a labeled assumption"}
        item = _find_plan_item(plan_items, SLOT_CATEGORIES[slot], used_items, SLOT_KEYWORDS[slot]) if plan_present else None
        if item is not None and not (slot == "tradeoff" and not plan_silent_done and _plan_gap_for(org_plan, slot)):
            used_items.add(item["id"])
            procedure = {
                "type": "org_plan", "ref": item["id"],
                "label": f"{item.get('document_title') or 'Plan'} {('section ' + str(item['section'])) if item.get('section') else ''} {item.get('label')}".strip(),
                "quote": item.get("quote"),
            }
        elif plan_present:
            gap = _plan_gap_for(org_plan, slot)
            procedure = {"type": "plan_silent", "ref": gap.get("id") if gap else None,
                         "label": f"Plan is silent on: {gap.get('topic') if gap else slot}", "quote": None}
            plan_silent_done = True
        else:
            acts = _pack_actions(pack, phase, 1)
            procedure = {"type": "pack_default", "ref": acts[0]["source"] if acts else f"pack_default:{pack.slug}",
                         "label": f"{pack.display_name} default: {acts[0]['text'] if acts else phase}", "quote": None}
        actions = []
        if procedure["type"] == "org_plan" and item is not None and item.get("category") in ACTIONABLE and item["id"] not in used_actions:
            actions.append(_action_from_item(item))
            used_actions.add(item["id"])
        if plan_present:
            actions += _plan_actions(plan_items, SLOT_ACTION_PHASES[slot], used_actions, SLOT_KEYWORDS[slot], 3 - len(actions),
                                     SLOT_ACTION_CATEGORIES.get(slot))
        if len(actions) < 2:
            have = {a["text"] for a in actions}
            pool = []
            for ph in [phase] + [p for p in SLOT_ACTION_PHASES[slot] if p != phase]:
                pool += _pack_actions(pack, ph, 10)
            for a in pool:
                if len(actions) >= 3:
                    break
                if a["source"] not in used_pack_actions and a["text"] not in have:
                    actions.append(a)
                    used_pack_actions.add(a["source"])
                    have.add(a["text"])
            if not actions:
                # every default for this phase is already tested earlier; test the first two again
                actions = _pack_actions(pack, phase, 2)
        actions = [a | {"id": f"I{i}-{a['id']}"} for a in actions]
        timings = [a.get("timing_minutes") for a in actions if a.get("timing_minutes")]
        if procedure["type"] == "org_plan" and item is not None and item.get("timing_minutes"):
            timings.insert(0, item["timing_minutes"])
        notify = [n for n in SLOT_NOTIFY[slot] if n in {p["id"] for p in pack.notify_parties}]
        flags: dict[str, Any] = {"conflicting_information": False, "business_tradeoff": False, "plan_silent": procedure["type"] == "plan_silent", "starts_clock": []}
        flags.update(SLOT_FLAGS.get(slot, {}))
        if slot == "notification" and clock_ids:
            flags["starts_clock"] = clock_ids
        text = _slot_text(slot, ctx, procedure, severity)
        injects.append({
            "id": f"I{i}",
            "order": i,
            "phase": phase,
            "slot": slot,
            "time_marker": _phase_marker(i, start_min),
            "minutes_offset": start_min,
            "time_budget_minutes": per_inject,
            "slide_number": slide,
            "title": text["title"],
            "what_happens": text["what_happens"],
            "recipients": text["recipients"],
            "decision_forced": text["decision_forced"],
            "decision_owner_role": _pick_role(roles, SLOT_OWNER_KEYS[slot]),
            "acceptable_owner_roles": [r for r in SLOT_ACCEPTABLE_OWNERS.get(slot, []) if r in {x["id"] for x in roles} and r != _pick_role(roles, SLOT_OWNER_KEYS[slot])],
            "plan_commitment_minutes": min(timings) if timings else None,
            "procedure_tested": procedure,
            "what_good_looks_like": text["good"],
            "where_teams_fail": text["fail"],
            "expected_actions": actions,
            "expected_notifications": notify,
            "hints": text["hints"],
            "probing_questions": text["probing"],
            "host_lines": text["host_lines"],
            "source": source,
            "flags": flags,
        })
        slide += 1

    # a 60-minute exercise has no dedicated conflict or tradeoff slot; mark them on existing injects
    if not any(j["flags"]["conflicting_information"] for j in injects):
        # put the contradiction on the first containment-phase inject (the second inject in a short exercise)
        k = next((n for n, j in enumerate(injects) if j["phase"] == "containment"), min(1, len(injects) - 1))
        injects[k]["flags"]["conflicting_information"] = True
        injects[k]["what_happens"] += _fmt(" Then a second report contradicts the first: the vendor says {entry_asset} was patched last month and the alert is a false positive, while the forensics lead says the patch was never applied.", ctx)
        injects[k]["probing_questions"].append("Two credible sources disagree. What do you do with containment while you find out which is right?")
    if not any(j["flags"]["business_tradeoff"] for j in injects):
        injects[-2]["flags"]["business_tradeoff"] = True
    if plan_present and not any(j["flags"]["plan_silent"] for j in injects):
        gap = _plan_gap_for(org_plan, "tradeoff")
        j = injects[-1]
        j["procedure_tested"] = {"type": "plan_silent", "ref": gap.get("id") if gap else None, "label": f"Plan is silent on: {gap.get('topic') if gap else 'this decision'}", "quote": None}
        j["flags"]["plan_silent"] = True
    if not plan_present and not any(j["flags"]["plan_silent"] for j in injects):
        j = injects[-1]
        j["procedure_tested"] = {"type": "plan_silent", "ref": None, "label": "No plan uploaded: this inject tests a decision the pack defaults do not cover (public statement approval)", "quote": None}
        j["flags"]["plan_silent"] = True

    researched = [c["id"] for c in applicable if c.get("tier") != "verified"]
    pack_doc = {
        "schema_version": "1",
        "generated_at": now_iso(),
        "generator": "ttx outline (deterministic skeleton; narrative to be refined by scenario_design)",
        "title": f"{org_name}: {family.title()} tabletop exercise (severity {severity}, {duration} minutes)",
        "slug": slugify(f"{org_name} {family} ttx"),
        "organization": org,
        "intake": intake,
        "pack": pack.slug,
        "pack_display_name": pack.display_name,
        "severity_level": severity,
        "severity_musts": _severity_musts(severity),
        "duration_minutes": duration,
        "audience": intake.get("audience") or "mixed",
        "scenario": {
            "family": family,
            "summary": _fmt("A {family} incident at {org} that begins with {entry_cve} on the internet-facing {entry_asset}, moves through {pivot_desc} by {pivot_technique}, and reaches {target_asset}, which holds {data_types}.", ctx),
            "path_source": seed.get("path_source"),
        },
        "seed": seed,
        "clocks": applicable,
        "clocks_outside_scenario": out_of_scenario,
        "clock_start_inject": next((j["id"] for j in injects if j["flags"]["starts_clock"]), None),
        "exercise_requirements": pack.exercise_requirements,
        "org_plan": org_plan or {"present": False, "source_documents": [], "items": [], "gaps": []},
        "roles": roles,
        "notify_parties": pack.notify_parties,
        "ground_rules": GROUND_RULES,
        "objectives": OBJECTIVES,
        "injects": injects,
        "hot_wash": {"questions": HOT_WASH},
        "next_steps": [
            "Score the decision tracker with ttx score and circulate the after-action report within five business days.",
            "Assign an owner and a date to every gap labeled plan, people, or technical.",
            "Promote any researched-tier clock to verified after a human checks the source.",
            "Schedule the rerun on the unfixed attack path next quarter.",
        ],
        "assumptions": list(seed.get("assumptions") or []),
        "banner": {
            "show": bool(researched),
            "text": BANNER_TEXT.format(ids=", ".join(researched)) if researched else "",
            "researched_clock_ids": researched,
        },
        "approval": {"approved": False, "approved_by": None, "approved_at": None, "outline_hash": None},
    }
    return pack_doc


def _and_join(items: list) -> str:
    items = [str(i) for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _deadline_words(clock: dict) -> str:
    h = clock.get("deadline_hours")
    if h is not None:
        return f"{int(h // 24)} days" if h >= 72 and h % 24 == 0 else f"{h:g} hours"
    if clock.get("deadline_business_days") is not None:
        return f"{clock['deadline_business_days']} business days"
    return "no fixed number of days"


def scenario_clocks(clocks: list[dict], scenario_data: list[str]) -> tuple[list[dict], list[dict]]:
    """Keep the clocks the scenario's data can trigger.

    A clock whose applies_when names data types applies to this scenario only if the
    crown jewel holds one of them; clocks with no data condition always stay. Chained
    clocks stay only if their parent stays. Dropped clocks are listed with the reason.
    """
    data = {str(d) for d in scenario_data}
    keep: list[dict] = []
    dropped: list[dict] = []
    for c in clocks:
        cond = c.get("applies_when") or {}
        wanted = {str(d) for d in as_list(cond.get("data_types"))}
        if wanted and not (wanted & data):
            dropped.append({"id": c["id"], "reason": f"scenario data {sorted(data)} does not include {sorted(wanted)}"})
        else:
            keep.append(c)
    kept_ids = {c["id"] for c in keep}
    final = []
    for c in keep:
        if c.get("after_clock") and c["after_clock"] not in kept_ids:
            dropped.append({"id": c["id"], "reason": f"runs after {c['after_clock']}, which is not in this scenario"})
        else:
            final.append(c)
    return final, dropped


def _plan_gap_for(org_plan: dict | None, slot: str) -> dict:
    gaps = list((org_plan or {}).get("gaps") or [])
    if not gaps:
        return {}
    keys = {"tradeoff": ["ransom", "shutdown", "diversion", "payment"], "public": ["public", "media", "statement", "press"],
            "conflict": ["conflict", "evidence"], "recovery": ["restore", "backup"], "notification": ["notif", "regulator"]}
    for key in keys.get(slot, []):
        for g in gaps:
            if key in (g.get("topic") or "").lower():
                return g
    return gaps[0]


def _severity_musts(severity: int) -> dict:
    table = {
        1: {"alert": True, "escalation": True},
        2: {"money_or_data_decision": True, "legal": True},
        3: {"outage": True, "ransom_note": True, "restore_order": True},
        4: {"three_pressures": True, "public_statement": True},
    }
    return table.get(severity, {})


def _slot_text(slot: str, ctx: dict, procedure: dict, severity: int) -> dict:
    plan_ref = procedure.get("label") or "the plan"
    T = {
        "detection": {
            "title": _fmt("First signal on {entry_asset}", ctx),
            "what_happens": _fmt("The security tool flags repeated authentication failures and a new administrative session on {entry_asset}, the internet-facing system that carries {entry_cve}. The analyst on shift is not sure whether it is a scan or a compromise.", ctx),
            "recipients": ["Security operations", "IT on-call"],
            "decision_forced": "Is this an incident, who gets told right now, and what severity does the analyst assign?",
            "good": _fmt("The analyst confirms the alert with a second source, opens an incident record with a timeline, and escalates to the incident lead within the time the plan commits to, citing {entry_asset} by name.", {"entry_asset": ctx["entry_asset"]}),
            "fail": "The analyst waits for more evidence, the alert sits in a queue, and nobody records when it was first seen.",
            "hints": ["Ask who is on call tonight and how they are reached.", "Ask what second source would confirm or clear the alert."],
            "probing": ["Who decides this is an incident, and does the analyst know that name?", "What severity would you assign and what in the plan says so?"],
            "host_lines": [_fmt("It is a Tuesday evening. Your security tooling has raised an alert on {entry_asset}. The analyst has a screen full of failed logins and one that succeeded. What do you do in the next fifteen minutes?", ctx)],
        },
        "second_signal": {
            "title": _fmt("Second signal: {pivot_asset}", ctx),
            "what_happens": _fmt("An hour later, logs show the same account authenticating to {pivot_asset}. The help desk reports two staff locked out of their accounts.", ctx),
            "recipients": ["Security operations", "Help desk"],
            "decision_forced": "Does the second signal change the severity, and who is told now?",
            "good": "The team links the two events, raises severity, and alerts the incident lead and the system owner for the second system.",
            "fail": "Two tickets exist for one incident and nobody connects them.",
            "hints": ["Ask whether the two tickets are linked.", "Ask who owns the second system."],
            "probing": ["What does the plan say about re-rating severity when scope grows?"],
            "host_lines": [_fmt("Sixty minutes on. The same account just logged into {pivot_asset}. Two users are locked out. Does this change anything?", ctx)],
        },
        "escalation": {
            "title": "Declaring the incident",
            "what_happens": _fmt("Evidence now shows the attacker holds an administrative session on {entry_asset} and has reached {pivot_desc} by {pivot_technique}. The incident lead must decide whether to declare, at what severity, and who is called in.", ctx),
            "recipients": ["Incident lead", "Executive on call"],
            "decision_forced": "Declare the incident and set the severity; name who is notified and in what order.",
            "good": _fmt("The incident lead declares the incident, assigns the severity the plan defines, and notifies leadership, counsel, and the cyber insurer in the order the plan sets ({plan_ref}).", {"plan_ref": plan_ref}),
            "fail": "Declaration is delayed to avoid alarming executives, counsel is not engaged, and the insurer is called after outside help has already been retained.",
            "hints": ["Ask for the exact phrase the plan uses for the declaration.", "Ask who calls the insurer."],
            "probing": ["What severity, and which sentence in the plan says so?", "Who is on the notification list for this severity and who calls them?"],
            "host_lines": [_fmt("The attacker is on {pivot_asset}. Is this an incident under your plan? Say the severity out loud and tell me who you are calling, in order.", ctx)],
        },
        "severity": {
            "title": "Scope grows",
            "what_happens": _fmt("Forensics finds the attacker created a new privileged account on {pivot_asset} three days ago. The intrusion is older than anyone assumed.", ctx),
            "recipients": ["Incident lead", "Security operations"],
            "decision_forced": "Re-rate the severity and decide whether the timeline resets any internal commitment.",
            "good": "The team re-rates severity, records the earliest known compromise date, and briefs leadership on what that date means for notifications.",
            "fail": "The team argues about the date instead of recording both candidates and moving on.",
            "hints": ["Ask what date goes in the regulator notice."],
            "probing": ["Which date is the discovery date under your plan and under the clock?"],
            "host_lines": ["Forensics calls: the account was created three days ago. Does your severity change, and what date goes on the notice?"],
        },
        "containment": {
            "title": _fmt("Containment on {pivot_asset}", ctx),
            "what_happens": _fmt("Containment options are on the table: isolate {entry_asset}, reset every privileged credential, and take {pivot_asset} offline. Each option cuts a service the business is using right now.", ctx),
            "recipients": ["Incident lead", "IT operations", "Business owners"],
            "decision_forced": "Which systems are isolated now, who authorizes it, and how is evidence preserved?",
            "good": _fmt("The team isolates the entry system, preserves images before rebuilding, resets privileged credentials, and names the person who authorized each action ({plan_ref}).", {"plan_ref": plan_ref}),
            "fail": "The team reimages the entry system before forensics has a copy, or waits for a perfect picture while the attacker keeps moving.",
            "hints": ["Ask whether anyone has taken a forensic image yet.", "Ask who can approve taking a production system offline."],
            "probing": ["Who authorizes the shutdown, and is that person in the room?", "What are you doing to preserve evidence before you contain?"],
            "host_lines": [_fmt("Your team can isolate {entry_asset} and {pivot_asset} right now. Doing so cuts remote access and authentication for the building. Who decides, and what do you say to the business?", ctx)],
        },
        "conflict": {
            "title": "Conflicting information",
            "what_happens": _fmt("Two reports arrive within minutes. The vendor says the vulnerability on {entry_asset} was patched last month and the alert is a false positive. The forensics lead says the patch was never applied and the attacker is still inside. Both are confident.", ctx),
            "recipients": ["Incident lead", "Vendor manager", "Forensics"],
            "decision_forced": "Which report do you act on, and what do you do while you find out which is true?",
            "good": "The team keeps containment in place, asks for the evidence behind each claim, and records both reports in the timeline.",
            "fail": "The team lifts containment on the vendor's word, or stalls entirely until the conflict is resolved.",
            "hints": ["Ask what evidence would settle it.", "Ask what happens to containment while they wait."],
            "probing": ["What does the plan say to do with contradictory information?", "Who owns the relationship with the vendor and are they in the room?"],
            "host_lines": ["The vendor says you are patched and fine. Your forensics lead says you are not. You have five minutes before leadership asks which one it is."],
        },
        "tradeoff": {
            "title": "The business tradeoff",
            "what_happens": _fmt("{target_asset} is confirmed affected and the {data_types} it holds may be exposed. Operations asks to keep the system running through the busiest hours of the day; security asks to take it down now. A ransom note has appeared on two systems.", ctx),
            "recipients": ["Executive leadership", "Incident lead", "Operations"],
            "decision_forced": "Keep the system up and accept the exposure, or take it down and accept the outage? Who makes that call?",
            "good": _fmt("The decision is made by the role the plan names, within minutes, with the reasons recorded, and the ransom question is routed to counsel and the insurer ({plan_ref}).", {"plan_ref": plan_ref}),
            "fail": "Nobody can name who holds the decision, so it drifts to whoever speaks loudest.",
            "hints": ["Ask who signs the shutdown order.", "Ask whether anyone has opened the ransom note's instructions."],
            "probing": ["Who holds this decision in your plan?", "What is the plan's position on ransom payment, and who is allowed to talk to the attacker?"],
            "host_lines": [_fmt("A ransom note is on screen. {target_asset} is affected. Operations wants to keep it running. Who decides, and what do they decide?", ctx)],
        },
        "recovery": {
            "title": _fmt("Restore order for {target_asset}", ctx),
            "what_happens": _fmt("Backups for {target_asset} exist but the last successful restore test was months ago. The business wants {target_asset} first; IT wants the identity systems first. Clinics and departments are working on paper until it is decided.", ctx),
            "recipients": ["IT operations", "Business owners", "Incident lead"],
            "decision_forced": "What is restored first, who approves the order, and what is the recovery time objective you are now working to?",
            "good": _fmt("The team checks the backups are clean before restoring, agrees a restore order with the business owners, and states the recovery objective from the plan ({plan_ref}).", {"plan_ref": plan_ref}),
            "fail": "The team restores from a backup that was never verified, or restores the crown jewel before the identity systems and loses it again.",
            "hints": ["Ask when the backup was last tested.", "Ask what the plan's recovery time objective is for this system."],
            "probing": ["What is your recovery time objective for this system and where is it written?", "How do you know the backup is clean?"],
            "host_lines": [_fmt("Backups exist. They were last tested months ago. The business wants {target_asset} back today. What is your restore order?", ctx)],
        },
        "notification": {
            "title": "The notification clock starts",
            "what_happens": _fmt("Counsel confirms that {data_types} on {target_asset} were accessed. The notification clocks start now. The tightest one belongs to {tight_clock}: {tight_deadline}.", ctx),
            "recipients": ["General counsel", "Compliance", "Executive leadership"],
            "decision_forced": "Which clocks apply, who owns each notification, and what is the first draft of the notice?",
            "good": _fmt("The team lists every applicable clock with its owner and due date, starts the regulator notice, and records the discovery date it will defend ({plan_ref}).", {"plan_ref": plan_ref}),
            "fail": "The team debates whether data was really taken instead of starting the clock, or assumes one notice covers every regulator.",
            "hints": ["Ask who owns the regulator relationship.", "Ask what date the team will put on the notice."],
            "probing": ["Which clock is tightest and who owns it?", "What does your plan commit to internally, and is it stricter than the regulator?"],
            "host_lines": [_fmt("Counsel says the data was accessed. Your clocks start now. Which ones apply, and who in this room owns each one?", ctx)],
        },
        "public": {
            "title": "The public statement",
            "what_happens": _fmt("A reporter has the ransom note and is calling the switchboard. Staff are posting on social media. Leadership wants a statement in the next hour; counsel wants to wait for facts.", ctx),
            "recipients": ["Communications", "Executive leadership", "General counsel"],
            "decision_forced": "Say something now or wait, and who approves the words?",
            "good": _fmt("A short holding statement goes out within the hour, approved by the roles the plan names, that promises updates without guessing at facts ({plan_ref}).", {"plan_ref": plan_ref}),
            "fail": "Leadership speaks without counsel, or counsel blocks every statement until the reporter publishes without the organization's voice.",
            "hints": ["Ask who approves the statement.", "Ask what the staff have already been told."],
            "probing": ["Who approves external statements in your plan?", "What have you told your own staff?"],
            "host_lines": ["The reporter is on the line. Leadership wants a statement in an hour. What do you say, and who signs it off?"],
        },
    }
    return T[slot]


EDITABLE_INJECT_FIELDS = {
    "title", "what_happens", "recipients", "decision_forced", "what_good_looks_like", "where_teams_fail",
    "hints", "probing_questions", "host_lines",
}
EDITABLE_TOP_FIELDS = {"scenario_summary", "objectives", "ground_rules", "hot_wash_questions", "next_steps"}


def apply_narrative(pack: dict, overlay: dict) -> dict:
    """Apply a narrative overlay written by the scenario_design skill.

    The overlay may change only narrative fields; ids, sources, procedures, expected
    actions, clocks, flags, and the seed are refused. Applying an overlay clears any
    approval, so the outline must be approved again.
    """
    unknown_top = set(overlay) - EDITABLE_TOP_FIELDS - {"injects", "_comment"}
    if unknown_top:
        raise ValueError(f"overlay may not set {sorted(unknown_top)}; editable: {sorted(EDITABLE_TOP_FIELDS)} and injects")
    by_id = {j["id"]: j for j in pack.get("injects", [])}
    for iid, fields in (overlay.get("injects") or {}).items():
        if iid not in by_id:
            raise ValueError(f"overlay names inject '{iid}', which is not in the outline")
        bad = set(fields) - EDITABLE_INJECT_FIELDS
        if bad:
            raise ValueError(f"overlay may not change {sorted(bad)} on {iid}; editable: {sorted(EDITABLE_INJECT_FIELDS)}")
        for key, value in fields.items():
            if key in {"recipients", "hints", "probing_questions", "host_lines"} and not isinstance(value, list):
                raise ValueError(f"{iid}.{key} must be a list")
            by_id[iid][key] = value
    if "scenario_summary" in overlay:
        pack.setdefault("scenario", {})["summary"] = overlay["scenario_summary"]
    if "hot_wash_questions" in overlay:
        pack.setdefault("hot_wash", {})["questions"] = overlay["hot_wash_questions"]
    for key in ("objectives", "ground_rules", "next_steps"):
        if key in overlay:
            pack[key] = overlay[key]
    pack["generator"] = "ttx outline skeleton + scenario_design narrative overlay"
    pack["approval"] = {"approved": False, "approved_by": None, "approved_at": None, "outline_hash": None}
    return pack


def stamp_approval(pack: dict, approved_by: str) -> dict:
    pack["approval"] = {"approved": False, "approved_by": None, "approved_at": None, "outline_hash": None}
    h = approval_hash(pack)
    pack["approval"] = {"approved": True, "approved_by": approved_by, "approved_at": now_iso(), "outline_hash": h}
    return pack
