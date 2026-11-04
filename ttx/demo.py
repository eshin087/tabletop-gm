"""One complete synthetic run: the sample exercise, end to end.

  intake + synthetic estate + synthetic IR plan
    -> seed, clocks, outline (deterministic skeleton)
    -> narrative overlay (samples/narrative_overlay_sample.json, written by the scenario_design skill)
    -> approval (by a labeled synthetic approver)
    -> deck, facilitator guide, handout, tracker, attendance, sign-off
    -> a synthetic completed tracker (what a host would record)
    -> score -> after-action report

No network, no keys, no model. Every decision recorded below is invented for
the sample. `ttx demo` runs it into out/demo; samples/make_sample_run.py runs it
into samples/outputs.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .common import REPO_ROOT, read_json, read_yaml, write_json

SAMPLES = REPO_ROOT / "samples"

# What a host might record during the exercise. Action entries name the plan item
# (P16) or pack default (d1) and are matched to the inject's expected action ids.
DECISIONS = {
    "detection": dict(
        decision="Analyst confirmed the session against firewall logs and paged the Director of Security Operations, who called the CISO.",
        decided_by_role="security_operations", discussion_minutes=8, scenario_minutes=25, notified="",
        actions=["P16", "d1"], plan_step_followed="yes", documented="partial",
        notes="No incident record opened until the CISO asked for one."),
    "escalation": dict(
        decision="CISO declared SEV1 and requested Hospital Command Center activation; CIO and Privacy Officer called; CIO briefed the CEO and General Counsel.",
        decided_by_role="incident_commander", discussion_minutes=9, scenario_minutes=20, notified="executive_leadership, legal_counsel",
        actions=["P35", "P17", "P18"], plan_step_followed="yes", documented="yes",
        notes="Nobody called the cyber insurer; General Counsel assumed the CFO would."),
    "containment": dict(
        decision="CISO isolated vpngw01 under SEV1 authority but kept dc1 online on the vendor's word that the gateway was patched; privileged credential resets started.",
        decided_by_role="incident_commander", discussion_minutes=12, scenario_minutes=45, notified="executive_leadership",
        actions=["P6", "P28"], plan_step_followed="partial", documented="yes",
        notes="Medical devices on the affected segment were not discussed."),
    "tradeoff": dict(
        decision="No decision on payment. The CFO opened contact with the insurer's negotiator before counsel joined; the room could not say who may talk to the attacker.",
        decided_by_role="cfo", discussion_minutes=14, scenario_minutes=40, notified="executive_leadership",
        actions=["P34", "P21"], plan_step_followed="n/a", documented="no",
        notes="Ransom note preserved. Downtime procedures activated by the CNO."),
    "recovery": dict(
        decision="CIO approved restoring Active Directory first and the EHR database second, after the Director of Infrastructure confirmed the backup predates the compromise.",
        decided_by_role="cio", discussion_minutes=9, scenario_minutes=None, notified="executive_leadership",
        actions=["P32", "P31"], plan_step_followed="yes", documented="yes",
        notes="No one could state the EHR recovery time objective; no test restore this year."),
    "notification": dict(
        decision="General Counsel owns the regulatory notices and the Privacy Officer owns patient letters; FBI and insurer notified. Nobody took the state health department report.",
        decided_by_role="general_counsel", discussion_minutes=11, scenario_minutes=None, notified="hhs_ocr, fbi, cyber_insurer, patients",
        actions=["P26", "P25", "P23"], plan_step_followed="partial", documented="yes",
        notes="Team debated whether data was really taken before starting the clock."),
    "public": dict(
        decision="Communications drafted a holding statement from the template, General Counsel reviewed it, and the CEO approved it.",
        decided_by_role="ceo", discussion_minutes=12, scenario_minutes=50, notified="executive_leadership, legal_counsel",
        actions=["P42", "P43"], plan_step_followed="yes", documented="yes",
        notes="Staff social media posting was raised and left unanswered."),
}
# Clocks sheet: owner role and planned notification hours after the clock starts.
CLOCKS = {
    "hipaa_individual_notice": ("privacy_officer", 700),
    "state_ca_individual_notice": ("privacy_officer", 700),
    "state_ca_ag_sample_notice": ("general_counsel", 1000),
    "hipaa_hhs_notice_500_or_more": ("general_counsel", 1200),
    "hipaa_media_notice": ("communications", 1500),
    # ca_health_facility_unauthorized_access_15bd: left blank on purpose (no owner, no plan)
}

GUIDE_TEXT = """Tabletop GM sample exercise (synthetic)
========================================

Valley Regional Health System is a fictional 1,200-employee health system. Everything
here was built by Tabletop GM from synthetic data, with no API key and no model call.

Open these first
  deck.pptx                         What the room sees on the projector. Speaker notes hold the host lines.
  facilitator_guide.docx            The script: what to read aloud, what the plan says, what good looks like.
  after_action_report.docx          The scored result: headline, clocks met or missed, gaps, plan coverage map.

Also built
  participant_handout.docx          For everyone at the table. No spoilers.
  decision_tracker.xlsx             The blank tracker the host fills in during the exercise.
  decision_tracker_completed.xlsx   The same tracker with invented answers, used for the sample score.
  attendance_signin.xlsx            Sign-in sheet for audit evidence.
  signoff_sheet.docx                Facilitator and sponsor sign-off.

Engine files (for the curious)
  seed.json                         The attack path picked from the synthetic exposure data, with the rule for each step.
  clocks.json                       Every notification deadline that applies, with its source and verification tier.
  exercise_pack.json                The approved outline. Every document above is built from this file only.
  score.json                        The deterministic score behind the after-action report.

To build an exercise for your own organization, run the launcher again and choose option 2,
or open the Tabletop GM folder in Claude Code and type /tabletop.
"""


def run_sample(out_dir: str | Path, sample_pack_path: str | Path | None = None,
               approver: str = "Sample approver (synthetic run; a human signs here in real use)") -> dict:
    """Run the whole sample pipeline into out_dir. Returns {"files": {...}, "headline": str}."""
    from openpyxl import load_workbook

    from .build import build_all
    from .build.aar import build_aar
    from .clock_engine import evaluate
    from .outline import apply_narrative, build_outline, stamp_approval
    from .plan_ingest import documents_index, ingest
    from .score_engine import score_tracker
    from .seed_engine import build_seed
    from .validators import validate_exercise_pack, validate_org_plan, validate_seed

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    intake = read_yaml(SAMPLES / "intake_valley_regional.yaml")
    org_plan = read_json(SAMPLES / "org_plan_sample.json")

    docs = documents_index(ingest([SAMPLES / "sample_ir_plan.md"]))
    plan_check = validate_org_plan(org_plan, docs)
    if not plan_check.ok:
        raise ValueError(plan_check.summary())

    seed = build_seed(intake, estate_file=str(SAMPLES / "synthetic_estate.json"))
    if not validate_seed(seed).ok:
        raise ValueError("sample seed failed validation")
    clocks = evaluate(intake)
    write_json(out / "seed.json", seed)
    write_json(out / "clocks.json", clocks)

    pack = build_outline(intake, seed, clocks, org_plan)
    apply_narrative(pack, read_json(SAMPLES / "narrative_overlay_sample.json"))
    check = validate_exercise_pack(pack)
    if not check.ok:
        raise ValueError(check.summary())
    narrative_warnings = [w for w in check.warnings if "narrative mentions" in w]
    if narrative_warnings:
        raise ValueError("; ".join(narrative_warnings))
    stamp_approval(pack, approver)
    write_json(out / "exercise_pack.json", pack)
    if sample_pack_path:
        write_json(sample_pack_path, pack)

    files = {k: str(v) for k, v in build_all(pack, out).items()}

    completed = out / "decision_tracker_completed.xlsx"
    shutil.copyfile(out / "decision_tracker.xlsx", completed)
    wb = load_workbook(completed)
    ws = wb["Decisions"]
    col = {c.value: i for i, c in enumerate(ws[1])}
    injects = {j["id"]: j for j in pack["injects"]}
    for row in ws.iter_rows(min_row=2):
        inj = injects.get(row[col["inject_id"]].value)
        if not inj:
            continue
        d = DECISIONS[inj["slot"]]
        ids = [a["id"] for a in inj["expected_actions"]]
        done = [i for i in ids if i.split("-", 1)[1] in d["actions"]]
        values = dict(d, actions_completed=", ".join(done))
        for key in ("decision", "decided_by_role", "discussion_minutes", "scenario_minutes", "notified",
                    "actions_completed", "plan_step_followed", "documented", "notes"):
            row[col[key]].value = values.get(key)
    wc = wb["Clocks"]
    ccol = {c.value: i for i, c in enumerate(wc[1])}
    for row in wc.iter_rows(min_row=2):
        cid = row[ccol["clock_id"]].value
        if cid in CLOCKS:
            row[ccol["owner_role"]].value, row[ccol["planned_notify_hours"]].value = CLOCKS[cid]
    wb.save(completed)
    files["decision_tracker_completed"] = str(completed)

    score = score_tracker(pack, completed)
    write_json(out / "score.json", score)
    files["after_action_report"] = str(build_aar(pack, score, out / "after_action_report.docx"))
    return {"files": files, "headline": score["headline"]}


def write_guide(out_dir: str | Path) -> Path:
    path = Path(out_dir) / "START_HERE.txt"
    path.write_text(GUIDE_TEXT, encoding="utf-8", newline="\n")
    return path


def open_folder(path: str | Path) -> bool:
    """Open a folder in the system file browser. Returns False when no desktop is available."""
    import os
    import subprocess
    import sys

    p = str(Path(path).resolve())
    try:
        if sys.platform.startswith("win"):
            os.startfile(p)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", p], check=False)
        else:
            subprocess.run(["xdg-open", p], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False
