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

from pathlib import Path

from .common import REPO_ROOT, read_json, read_yaml, write_json

SAMPLES = REPO_ROOT / "samples"

# What a host might pick in the tracker during the exercise (dropdown text, as the host sees it).
# Action entries name the plan item (P16) or pack default (d1); they are matched to the inject's
# expected action ids. Every answer below is invented for the sample.
DECISIONS = {
    "detection": dict(
        decided_by="security_operations", speed="Within 30 minutes", discussion="10", actions=["P16", "d1"], notified=[],
        plan_step="Yes", documented="Partly",
        decision="Analyst confirmed the session against firewall logs and paged the Director of Security Operations, who called the CISO.",
        notes="No incident record opened until the CISO asked for one."),
    "escalation": dict(
        decided_by="incident_commander", speed="Within 30 minutes", discussion="10", actions=["P35", "P17", "P18"],
        notified=["executive_leadership", "legal_counsel"], plan_step="Yes", documented="Yes",
        decision="CISO declared SEV1 and requested Hospital Command Center activation; CIO and Privacy Officer called; CIO briefed the CEO and General Counsel.",
        notes="Nobody called the cyber insurer; General Counsel assumed the CFO would."),
    "containment": dict(
        decided_by="incident_commander", speed="Within 1 hour", discussion="15", actions=["P6", "P28"],
        notified=["executive_leadership"], plan_step="Partly", documented="Yes",
        decision="CISO isolated vpngw01 under SEV1 authority but kept dc1 online on the vendor's word that the gateway was patched; privileged credential resets started.",
        notes="Medical devices on the affected segment were not discussed."),
    "tradeoff": dict(
        decided_by="cfo", speed="Not stated", discussion="15", actions=["P34", "P21"], notified=["executive_leadership"],
        plan_step="Not applicable", documented="No",
        decision="No decision on payment. The CFO opened contact with the insurer's negotiator before counsel joined; the room could not say who may talk to the attacker.",
        notes="Ransom note preserved. Downtime procedures activated by the CNO."),
    "recovery": dict(
        decided_by="cio", speed="Not stated", discussion="10", actions=["P32", "P31"], notified=["executive_leadership"],
        plan_step="Yes", documented="Yes",
        decision="CIO approved restoring Active Directory first and the EHR database second, after the Director of Infrastructure confirmed the backup predates the compromise.",
        notes="No one could state the EHR recovery time objective; no test restore this year."),
    "notification": dict(
        decided_by="general_counsel", speed="Not stated", discussion="10", actions=["P26", "P25", "P23"],
        notified=["hhs_ocr", "fbi", "cyber_insurer", "patients"], plan_step="Partly", documented="Yes",
        decision="General Counsel owns the regulatory notices and the Privacy Officer owns patient letters; FBI and insurer notified. Nobody took the state health department report.",
        notes="Team debated whether data was really taken before starting the clock."),
    "public": dict(
        decided_by="ceo", speed="Within 1 hour", discussion="15", actions=["P42", "P43"],
        notified=["executive_leadership", "legal_counsel"], plan_step="Yes", documented="Yes",
        decision="Communications drafted a holding statement from the template, General Counsel reviewed it, and the CEO approved it.",
        notes="Staff social media posting was raised and left unanswered."),
}
# Notification clocks sheet: who owns each notice and when the team plans to send it.
CLOCKS = {
    "hipaa_individual_notice": ("privacy_officer", "Within 30 days"),
    "state_ca_individual_notice": ("privacy_officer", "Within 30 days"),
    "state_ca_ag_sample_notice": ("general_counsel", "Within 15 days"),
    "hipaa_hhs_notice_500_or_more": ("general_counsel", "Within 60 days"),
    "hipaa_media_notice": ("communications", "Within 90 days"),
    # ca_health_facility_unauthorized_access_15bd: left blank on purpose (no owner, no plan)
}

GUIDE_TEXT = """Tabletop GM sample exercise (synthetic)
========================================

Valley Regional Health System is a fictional 1,200-employee health system. Everything
here was built by Tabletop GM from synthetic data, with no API key and no model call.

Open these first
  deck.pptx                         What the room sees on the projector. Speaker notes hold the host lines.
  facilitator_guide.docx            The script: what to read aloud, what the plan says, what good looks like.
  after_action_report.docx          The scored result in about two pages: rating, lessons learned, each decision,
                                    deadlines met or missed, and the action plan. Auditor detail is in the appendix.
  executive_summary.pptx            Seven slides for senior management: rating, regulatory exposure, risks,
                                    lessons learned, fixes, asks.
  executive_summary.docx            The same summary as a one-page memo to send ahead of the meeting.

Also built
  participant_handout.docx          For everyone at the table. No spoilers.
  decision_tracker.xlsx             The blank tracker the host fills in during the exercise (dropdowns and Yes/No).
  decision_tracker_completed.xlsx   The same tracker filled with invented answers, used for the sample score.
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
    from .build import build_all
    from .build.tracker import fill_host_tracker
    from .build.aar import build_aar
    from .build.exec_summary import build_exec_deck, build_exec_memo
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
    by_inject = {}
    for inj in pack["injects"]:
        d = dict(DECISIONS[inj["slot"]])
        ids = [a["id"] for a in inj["expected_actions"]]
        d["actions"] = [i for i in ids if i.split("-", 1)[1] in d["actions"]]
        by_inject[inj["id"]] = d
    fill_host_tracker(out / "decision_tracker.xlsx", pack, by_inject, CLOCKS, out_path=completed)
    files["decision_tracker_completed"] = str(completed)

    score = score_tracker(pack, completed)
    write_json(out / "score.json", score)
    files["after_action_report"] = str(build_aar(pack, score, out / "after_action_report.docx"))
    files["executive_summary_slides"] = str(build_exec_deck(pack, score, out / "executive_summary.pptx"))
    files["executive_summary_memo"] = str(build_exec_memo(pack, score, out / "executive_summary.docx"))
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
