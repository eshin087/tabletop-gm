import copy
import csv
import json
import shutil
from pathlib import Path

import pytest

from ttx.common import read_json
from ttx.score_engine import DECISION_COLUMNS, read_tracker, score_clocks, score_inject, score_tracker

OUTPUTS = Path("samples/outputs")


@pytest.fixture
def completed():
    return OUTPUTS / "decision_tracker_completed.xlsx"


def test_same_tracker_same_score_every_time(sample_pack, completed, tmp_path):
    a = score_tracker(sample_pack, completed)
    copy_path = tmp_path / completed.name
    shutil.copyfile(completed, copy_path)
    b = score_tracker(copy.deepcopy(sample_pack), copy_path)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_committed_sample_score_matches_a_fresh_score(sample_pack, completed):
    fresh = score_tracker(sample_pack, completed)
    committed = read_json(OUTPUTS / "score.json")
    assert fresh == committed


def test_blank_tracker_means_not_reached(sample_pack):
    result = score_tracker(sample_pack, OUTPUTS / "decision_tracker.xlsx")
    assert result["summary"]["injects_scored"] == 0
    assert all(not r["reached"] for r in result["injects"])
    # the technical gaps exist regardless of how the room performed
    assert sum(1 for g in result["gaps"] if g["label"] == "technical") == len(sample_pack["seed"]["findings_cited"])


def _inj(sample_pack, slot):
    return next(j for j in sample_pack["injects"] if j["slot"] == slot)


def test_right_owner_scoring(sample_pack):
    inj = _inj(sample_pack, "escalation")
    base = {"decision": "declared", "documented": "yes"}
    assert score_inject(inj, dict(base, decided_by_role=inj["decision_owner_role"]), sample_pack, [])["scores"]["right_owner"] == 3
    assert score_inject(inj, dict(base, decided_by_role="cfo"), sample_pack, [])["scores"]["right_owner"] == 2
    assert score_inject(inj, dict(base, decided_by_role="someone_else"), sample_pack, [])["scores"]["right_owner"] == 1
    assert score_inject(inj, dict(base, decided_by_role=None), sample_pack, [])["scores"]["right_owner"] == 1


def test_timely_against_plan_commitment(sample_pack):
    inj = _inj(sample_pack, "detection")
    assert inj["plan_commitment_minutes"] == 15  # IR Plan 4.1: 15 minutes
    row = {"decision": "x", "decided_by_role": inj["decision_owner_role"], "documented": "yes"}
    assert score_inject(inj, dict(row, scenario_minutes=10), sample_pack, [])["scores"]["timely"] == 3
    assert score_inject(inj, dict(row, scenario_minutes=25), sample_pack, [])["scores"]["timely"] == 2
    assert score_inject(inj, dict(row, scenario_minutes=45), sample_pack, [])["scores"]["timely"] == 1


def test_plan_silent_inject_is_not_scored_on_plan_but_is_a_plan_gap(sample_pack, completed):
    result = score_tracker(sample_pack, completed)
    silent = [j["id"] for j in sample_pack["injects"] if j["procedure_tested"]["type"] == "plan_silent"]
    assert silent
    for r in result["injects"]:
        if r["inject_id"] in silent:
            assert r["scores"]["followed_plan"] is None
    assert any(g["label"] == "plan" and g["inject_id"] in silent for g in result["gaps"])


def test_clock_met_missed_and_unplanned(sample_pack):
    rows = {
        "hipaa_individual_notice": {"owner_role": "privacy_officer", "planned_notify_hours": 1000},
        "hipaa_media_notice": {"owner_role": "communications", "planned_notify_hours": 1500},
    }
    res = {c["clock_id"]: c for c in score_clocks(sample_pack, rows)}
    assert res["hipaa_individual_notice"]["status"] == "met" and res["hipaa_individual_notice"]["margin_hours"] == 440
    assert res["hipaa_individual_notice"]["internal_met"] is True  # plan's own 45 days is 1080 hours
    assert res["hipaa_media_notice"]["status"] == "missed" and res["hipaa_media_notice"]["margin_hours"] == -60
    assert res["hipaa_hhs_notice_500_or_more"]["status"] == "not_planned"


def test_chained_clock_runs_from_parent_notice(sample_pack):
    if not any(c["id"] == "state_ca_ag_sample_notice" for c in sample_pack["clocks"]):
        pytest.skip("CA AG clock not in sample")
    rows = {"state_ca_individual_notice": {"owner_role": "privacy_officer", "planned_notify_hours": 700},
            "state_ca_ag_sample_notice": {"owner_role": "general_counsel", "planned_notify_hours": 1000}}
    res = {c["clock_id"]: c for c in score_clocks(sample_pack, rows)}
    assert res["state_ca_ag_sample_notice"]["deadline_hours"] == 700 + 360
    assert res["state_ca_ag_sample_notice"]["status"] == "met"
    rows.pop("state_ca_individual_notice")
    res = {c["clock_id"]: c for c in score_clocks(sample_pack, rows)}
    assert res["state_ca_ag_sample_notice"]["status"] == "not_planned"


def test_incident_timestamps_override_planned_hours(sample_pack, tmp_path):
    incident = tmp_path / "incident.json"
    incident.write_text(json.dumps({"trigger_at": "2026-11-06T09:00:00Z",
                                    "notifications": {"hipaa_individual_notice": "2026-11-26T09:00:00Z"}}), encoding="utf-8")
    res = {c["clock_id"]: c for c in score_clocks(sample_pack, {}, read_json(incident))}
    assert res["hipaa_individual_notice"]["planned_notify_hours"] == 480
    assert res["hipaa_individual_notice"]["basis"] == "incident timestamps"


def test_csv_decision_log_scores_like_xlsx(sample_pack, completed, tmp_path):
    tracker = read_tracker(completed)
    path = tmp_path / "log.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=DECISION_COLUMNS)
        w.writeheader()
        for row in tracker["decisions"].values():
            w.writerow({k: row.get(k) for k in DECISION_COLUMNS})
    clocks_path = tmp_path / "log_clocks.csv"
    with open(clocks_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["clock_id", "owner_role", "planned_notify_hours"])
        w.writeheader()
        for cid, row in tracker["clocks"].items():
            w.writerow({"clock_id": cid, "owner_role": row.get("owner_role"), "planned_notify_hours": row.get("planned_notify_hours")})
    a = score_tracker(sample_pack, completed)
    b = score_tracker(sample_pack, path)
    assert a["summary"] == b["summary"]
    assert [g["finding"] for g in a["gaps"]] == [g["finding"] for g in b["gaps"]]


def test_coverage_map_counts_every_plan_item(sample_pack, completed):
    result = score_tracker(sample_pack, completed)
    cov = result["coverage"]
    assert cov["present"]
    assert len(cov["rows"]) == len(sample_pack["org_plan"]["items"])
    assert sum(cov["counts"][k] for k in ("followed", "deviated", "not_reached", "not_covered")) == len(cov["rows"])


def test_gaps_cite_plan_quotes_verbatim(sample_pack, completed):
    result = score_tracker(sample_pack, completed)
    quotes = [i["quote"] for i in sample_pack["org_plan"]["items"]]
    for g in result["gaps"]:
        if g["label"] in {"people", "plan"} and g["citation"].startswith("IR Plan"):
            cited = g["citation"].split(": \"", 1)[1].rstrip("\"")
            assert cited in quotes
