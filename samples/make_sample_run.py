"""One complete synthetic run into samples/outputs/.

  intake + synthetic estate + synthetic IR plan
    -> seed, clocks, outline (deterministic skeleton)
    -> approval (by a labeled synthetic approver)
    -> deck, facilitator guide, handout, tracker, attendance, sign-off
    -> a synthetic completed tracker (what a host would record)
    -> score -> after-action report

No network, no keys, no model. Every decision recorded below is invented for
the sample. Run from the repo root:  python samples/make_sample_run.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from openpyxl import load_workbook  # noqa: E402

from ttx.build import build_all  # noqa: E402
from ttx.build.aar import build_aar  # noqa: E402
from ttx.clock_engine import evaluate  # noqa: E402
from ttx.common import read_json, read_yaml, write_json  # noqa: E402
from ttx.outline import build_outline, stamp_approval  # noqa: E402
from ttx.plan_ingest import documents_index, ingest  # noqa: E402
from ttx.score_engine import score_tracker  # noqa: E402
from ttx.seed_engine import build_seed  # noqa: E402
from ttx.validators import validate_exercise_pack, validate_org_plan, validate_seed  # noqa: E402

SAMPLES = REPO / "samples"
OUT = SAMPLES / "outputs"

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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    intake = read_yaml(SAMPLES / "intake_valley_regional.yaml")
    org_plan = read_json(SAMPLES / "org_plan_sample.json")

    docs = documents_index(ingest([SAMPLES / "sample_ir_plan.md"]))
    plan_check = validate_org_plan(org_plan, docs)
    assert plan_check.ok, plan_check.summary()

    seed = build_seed(intake, estate_file=str(SAMPLES / "synthetic_estate.json"))
    assert validate_seed(seed).ok
    clocks = evaluate(intake)
    write_json(OUT / "seed.json", seed)
    write_json(OUT / "clocks.json", clocks)

    pack = build_outline(intake, seed, clocks, org_plan)
    check = validate_exercise_pack(pack)
    assert check.ok, check.summary()
    stamp_approval(pack, "Sample approver (synthetic run; a human signs here in real use)")
    write_json(SAMPLES / "exercise_pack_sample.json", pack)
    shutil.copyfile(SAMPLES / "exercise_pack_sample.json", OUT / "exercise_pack.json")

    built = build_all(pack, OUT)
    for name, path in built.items():
        print(f"built {name:<20} {Path(path).relative_to(REPO)}")

    # fill a copy of the tracker the way a host would
    completed = OUT / "decision_tracker_completed.xlsx"
    shutil.copyfile(OUT / "decision_tracker.xlsx", completed)
    wb = load_workbook(completed)
    ws = wb["Decisions"]
    header = [c.value for c in ws[1]]
    col = {h: i for i, h in enumerate(header)}
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
    cheader = [c.value for c in wc[1]]
    ccol = {h: i for i, h in enumerate(cheader)}
    for row in wc.iter_rows(min_row=2):
        cid = row[ccol["clock_id"]].value
        if cid in CLOCKS:
            row[ccol["owner_role"]].value, row[ccol["planned_notify_hours"]].value = CLOCKS[cid]
    wb.save(completed)

    score = score_tracker(pack, completed)
    write_json(OUT / "score.json", score)
    aar = build_aar(pack, score, OUT / "after_action_report.docx")
    print(f"built after_action_report    {aar.relative_to(REPO)}")
    print("headline:", score["headline"])


if __name__ == "__main__":
    main()
