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

from .common import as_list, now_iso, slugify
from .packs import load_pack
from .validators import approval_hash

SLOT_PLANS: dict[int, list[str]] = {
    60: ["detection", "escalation", "containment", "recovery", "notification"],
    90: ["detection", "escalation", "containment", "conflict", "recovery", "notification", "public"],
    180: ["detection", "second_signal", "escalation", "severity", "containment", "conflict", "tradeoff", "recovery", "notification", "public"],
}
PHASE_OF_SLOT = {
    "detection": "detection", "second_signal": "detection", "escalation": "escalation", "severity": "escalation",
    "containment": "containment", "conflict": "containment", "tradeoff": "containment", "recovery": "recovery",
    "notification": "notification", "public": "notification",
}
SLOT_CATEGORIES = {
    "detection": ["severity_level", "role"],
    "second_signal": ["escalation_step", "role"],
    "escalation": ["escalation_step", "decision_authority"],
    "severity": ["severity_level", "decision_authority"],
    "containment": ["containment_procedure", "playbook_step", "decision_authority"],
    "conflict": ["playbook_step", "containment_procedure"],
    "tradeoff": ["decision_authority", "containment_procedure"],
    "recovery": ["recovery_objective", "playbook_step"],
    "notification": ["notification_procedure", "decision_authority"],
    "public": ["comms_template", "notification_procedure"],
}
SLOT_OWNER_KEYS = {
    "detection": ["ciso", "incident_commander", "security_operations"],
    "second_signal": ["ciso", "incident_commander"],
    "escalation": ["incident_commander", "ciso"],
    "severity": ["ciso", "incident_commander"],
    "containment": ["cio", "incident_commander", "ciso"],
    "conflict": ["incident_commander", "ciso"],
    "tradeoff": ["ceo", "incident_commander", "coo"],
    "recovery": ["cio", "incident_commander"],
    "notification": ["general_counsel", "privacy_officer", "compliance_officer", "legal"],
    "public": ["communications", "ceo", "comms"],
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
    "public": {"business_tradeoff": True},
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


def _find_plan_item(items: list[dict], categories: list[str], used: set[str]) -> dict | None:
    for cat in categories:
        for item in items:
            if item.get("category") == cat and item.get("id") not in used:
                return item
    for cat in categories:
        for item in items:
            if item.get("category") == cat:
                return item
    return None


def _plan_actions(items: list[dict], phase: str, limit: int = 3) -> list[dict]:
    out = []
    for item in items:
        if item.get("phase") == phase and item.get("category") in {"playbook_step", "escalation_step", "notification_procedure", "containment_procedure", "recovery_objective"}:
            out.append({"id": item["id"], "text": item.get("value") or item.get("label"), "source": f"org_plan:{item['id']}"})
        if len(out) >= limit:
            break
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
    applicable = list(clocks.get("clocks") or [])
    clock_ids = [c["id"] for c in applicable]
    tight = sorted([c for c in applicable if c.get("deadline_hours") is not None], key=lambda c: c["deadline_hours"])
    tight_clock = tight[0] if tight else (applicable[0] if applicable else None)
    ctx = {
        "org": org_name,
        "entry_asset": entry.get("asset"),
        "entry_cve": entry.get("cve") or "a publicly known vulnerability",
        "entry_finding": entry.get("finding_id") or entry.get("assumption"),
        "pivot_asset": pivot.get("asset"),
        "pivot_technique": pivot.get("technique"),
        "target_asset": target.get("asset"),
        "data_types": ", ".join(target.get("data") or as_list(intake.get("data_types"))),
        "family": family,
        "tight_clock": tight_clock["name"] if tight_clock else "the applicable notification clock",
        "tight_deadline": tight_clock["deadline_text"] if tight_clock else "",
    }

    slots = SLOT_PLANS[duration]
    per_inject = (duration - 20) // len(slots)
    used_items: set[str] = set()
    injects: list[dict] = []
    slide = 6
    source_cycle = {
        "detection": ("entry", entry), "second_signal": ("entry", entry), "escalation": ("entry", entry),
        "severity": ("pivot", pivot), "containment": ("pivot", pivot), "conflict": ("pivot", pivot),
        "tradeoff": ("target", target), "recovery": ("target", target), "notification": ("target", target), "public": ("target", target),
    }
    plan_silent_done = False
    for i, slot in enumerate(slots, start=1):
        phase = PHASE_OF_SLOT[slot]
        start_min = 10 + (i - 1) * per_inject
        part_name, part = source_cycle[slot]
        if part.get("finding_id"):
            source = {"type": "finding", "ref": part["finding_id"], "note": f"{part_name} finding on {part.get('asset')}"}
        else:
            source = {"type": "assumption", "ref": part.get("assumption") or seed["assumptions"][0]["id"], "note": f"{part_name} is a labeled assumption"}
        item = _find_plan_item(plan_items, SLOT_CATEGORIES[slot], used_items) if plan_present else None
        if item is not None and not (slot in ("tradeoff", "public") and not plan_silent_done and plan_present and _plan_gap_for(org_plan, slot)):
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
        actions = _plan_actions(plan_items, phase) if plan_present else []
        if len(actions) < 2:
            actions += _pack_actions(pack, phase, 3 - len(actions))
        actions = [a | {"id": f"I{i}-{a['id']}"} for a in actions]
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
            "acceptable_owner_roles": [],
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
        injects[2]["flags"]["conflicting_information"] = True
        injects[2]["what_happens"] += " A second report contradicts the first: the help desk says the gateway was patched last month."
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
            "summary": _fmt("A {family} incident at {org} that begins with {entry_cve} on the internet-facing {entry_asset}, moves through {pivot_asset} by {pivot_technique}, and reaches {target_asset}, which holds {data_types}.", ctx),
            "path_source": seed.get("path_source"),
        },
        "seed": seed,
        "clocks": applicable,
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
            "text": clocks.get("banner", {}).get("text", ""),
            "researched_clock_ids": researched,
        },
        "approval": {"approved": False, "approved_by": None, "approved_at": None, "outline_hash": None},
    }
    return pack_doc


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
            "what_happens": _fmt("The security tool flags repeated authentication failures and a new administrative session on {entry_asset}, the internet-facing system carrying {entry_cve} (finding {entry_finding}). The analyst on shift is not sure whether it is a scan or a compromise.", ctx),
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
            "what_happens": _fmt("Evidence now shows the attacker holds an administrative session on {entry_asset} and has reached {pivot_asset} by {pivot_technique}. The incident lead must decide whether to declare, at what severity, and who is called in.", ctx),
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
            "what_happens": _fmt("{target_asset} is confirmed affected and {data_types} may be exposed. Operations asks to keep the system running through the busiest hours of the day; security asks to take it down now. A ransom note has appeared on two systems.", ctx),
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
            "what_happens": _fmt("Backups for {target_asset} exist but the last successful restore test was months ago. The business wants {target_asset} first; IT wants the identity systems first. Three days of work are at stake either way.", ctx),
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
            "what_happens": _fmt("Counsel confirms that {data_types} on {target_asset} were accessed. The notification clocks start now. The tightest one is {tight_clock}: {tight_deadline}.", ctx),
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


def stamp_approval(pack: dict, approved_by: str) -> dict:
    pack["approval"] = {"approved": False, "approved_by": None, "approved_at": None, "outline_hash": None}
    h = approval_hash(pack)
    pack["approval"] = {"approved": True, "approved_by": approved_by, "approved_at": now_iso(), "outline_hash": h}
    return pack
