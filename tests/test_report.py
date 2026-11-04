"""After the exercise: the host tracker round trip, `ttx report`, and the executive summary."""

import copy
import json
import shutil
from pathlib import Path

import pytest
from docx import Document
from pptx import Presentation

from ttx.build.exec_summary import build_content, rating_for
from ttx.build.tracker import CLOCK_TIMING, SPEED, build_tracker, fill_host_tracker
from ttx.report import find_tracker, run_report
from ttx.score_engine import read_tracker, score_tracker


def _fill(pack, path, out):
    inj = pack["injects"][0]
    second = pack["injects"][1]
    decisions = {
        inj["id"]: {"decided_by": inj["decision_owner_role"], "speed": "Within 15 minutes", "discussion": "10",
                    "actions": [a["id"] for a in inj["expected_actions"]], "notified": list(inj["expected_notifications"]),
                    "plan_step": "Yes", "documented": "Yes", "decision": "Declared and escalated.", "notes": "fast"},
        second["id"]: {"decided_by": "cfo", "speed": "Next day or later", "discussion": "30", "actions": [], "notified": [],
                       "plan_step": "The plan was unclear", "documented": "No"},
    }
    clocks = {pack["clocks"][0]["id"]: ("general_counsel", "Within 15 days")}
    return fill_host_tracker(path, pack, decisions, clocks, out_path=out)


def test_host_tracker_round_trip(sample_pack, tmp_path):
    blank = build_tracker(sample_pack, tmp_path / "t.xlsx")
    filled = _fill(sample_pack, blank, tmp_path / "filled.xlsx")
    t = read_tracker(filled)
    first, second = sample_pack["injects"][0], sample_pack["injects"][1]
    d1 = t["decisions"][first["id"]]
    assert d1["decided_by_role"] == first["decision_owner_role"]
    assert d1["scenario_minutes"] == SPEED["Within 15 minutes"]
    assert d1["discussion_minutes"] == 10
    assert set(d1["actions_completed"].split(", ")) == {a["id"] for a in first["expected_actions"]}
    assert d1["plan_step_followed"] == "yes" and d1["documented"] == "yes"
    d2 = t["decisions"][second["id"]]
    assert d2["decided_by_role"] == "cfo" and d2["plan_step_followed"] == "plan_unclear"
    assert d2["actions_completed"] == ""
    assert len(t["decisions"]) == 2  # unanswered injects count as not reached
    cid = sample_pack["clocks"][0]["id"]
    assert t["clocks"][cid]["owner_role"] == "general_counsel"
    assert t["clocks"][cid]["planned_notify_hours"] == CLOCK_TIMING["Within 15 days"]
    assert t["meta"]["outline_hash"] == sample_pack["approval"]["outline_hash"]


def test_typed_clock_timing_is_understood(sample_pack, tmp_path):
    from openpyxl import load_workbook

    path = build_tracker(sample_pack, tmp_path / "t.xlsx")
    wb = load_workbook(path)
    ws = wb["Notification clocks"]
    ws["D5"], ws["E5"] = "General Counsel", "Within 50 days"
    wb["Host tracker"]["C6"] = "Yes"  # one answer so the tracker counts as filled
    wb.save(path)
    t = read_tracker(path)
    assert t["clocks"][ws["A5"].value]["planned_notify_hours"] == 50 * 24


def test_report_finds_the_right_tracker_and_writes_everything(sample_pack, tmp_path):
    (tmp_path / "out").mkdir()
    (tmp_path / "uploads").mkdir()
    (tmp_path / "out" / "exercise_pack.json").write_text(json.dumps(sample_pack), encoding="utf-8")
    # a tracker for a different exercise and an empty one must both be skipped
    other = copy.deepcopy(sample_pack)
    other["approval"]["outline_hash"] = "0" * 64
    other_blank = build_tracker(other, tmp_path / "other_blank.xlsx")
    _fill(other, other_blank, tmp_path / "uploads" / "other_exercise.xlsx")
    build_tracker(sample_pack, tmp_path / "uploads" / "empty.xlsx")
    blank = build_tracker(sample_pack, tmp_path / "blank.xlsx")
    _fill(sample_pack, blank, tmp_path / "uploads" / "filled.xlsx")

    path, notes = find_tracker(sample_pack, root=tmp_path)
    assert path.name == "filled.xlsx" and notes == []

    result = run_report(root=tmp_path)
    out = Path(result["out"])
    for name in ("score.json", "after_action_report.docx", "executive_summary.pptx", "executive_summary.docx"):
        assert (out / name).exists(), name
    assert result["rating"] in {"Strong", "Adequate", "Needs work"}


def test_report_explains_when_no_tracker_is_filled(sample_pack, tmp_path):
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "exercise_pack.json").write_text(json.dumps(sample_pack), encoding="utf-8")
    build_tracker(sample_pack, tmp_path / "out" / "decision_tracker.xlsx")
    with pytest.raises(FileNotFoundError, match="no answers yet"):
        run_report(root=tmp_path)


def test_report_refuses_an_unapproved_exercise(sample_pack, tmp_path):
    pack = copy.deepcopy(sample_pack)
    pack["approval"]["approved"] = False
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "exercise_pack.json").write_text(json.dumps(pack), encoding="utf-8")
    with pytest.raises(ValueError, match="not approved"):
        run_report(root=tmp_path)


def test_executive_summary_content(sample_pack):
    score = score_tracker(sample_pack, "samples/outputs/decision_tracker_completed.xlsx")
    c = build_content(sample_pack, score)
    assert c["rating"] == rating_for(score["summary"]["percent"])[0]
    assert str(score["summary"]["percent"]) in c["headline"]
    assert 1 <= len(c["risks"]) <= 3
    assert 1 <= len(c["actions"]) <= 5
    assert any("counsel" in a for a in c["asks"])  # researched clocks need a legal check
    for f in sample_pack["seed"]["findings_cited"]:
        assert f not in json.dumps(c)  # no finding IDs for executives


def test_rating_thresholds():
    assert rating_for(90)[0] == "Strong"
    assert rating_for(85)[0] == "Strong"
    assert rating_for(84.9)[0] == "Adequate"
    assert rating_for(70)[0] == "Adequate"
    assert rating_for(69.9)[0] == "Needs work"


def test_executive_outputs_are_short(sample_pack, tmp_path):
    from ttx.build.exec_summary import build_exec_deck, build_exec_memo

    score = score_tracker(sample_pack, "samples/outputs/decision_tracker_completed.xlsx")
    deck = Presentation(str(build_exec_deck(sample_pack, score, tmp_path / "e.pptx")))
    assert len(deck.slides) == 7  # title, bottom line, exposure, risks, lessons learned, fixes, asks
    memo = Document(str(build_exec_memo(sample_pack, score, tmp_path / "e.docx")))
    words = sum(len(p.text.split()) for p in memo.paragraphs) + sum(len(c.text.split()) for t in memo.tables for r in t.rows for c in r.cells)
    assert words < 650, words  # one page
    text = "\n".join(p.text for p in memo.paragraphs)
    assert chr(0x2014) not in text


# --------------------------------------------------------------------------- #
# Demo responses (for a pitch or a practice run)
# --------------------------------------------------------------------------- #

def test_demo_responses_fit_any_exercise(sample_pack):
    from ttx.demo_responses import demo_answers

    decisions, clocks = demo_answers(sample_pack)
    assert set(decisions) == {j["id"] for j in sample_pack["injects"]}
    roles = {r["id"] for r in sample_pack["roles"]}
    for inj in sample_pack["injects"]:
        d = decisions[inj["id"]]
        assert d["decided_by"] in roles
        assert set(d["actions"]) <= {a["id"] for a in inj["expected_actions"]}
        assert set(d["notified"]) <= set(inj["expected_notifications"])
        assert "{" not in d["decision"] + d["notes"]  # every token filled from the exercise
    assert any(d["decided_by"] != j["decision_owner_role"] for j, d in ((j, decisions[j["id"]]) for j in sample_pack["injects"]))
    assert 0 < len(clocks) < len(sample_pack["clocks"])  # one notice is left unplanned on purpose


def test_report_demo_writes_marked_reports_without_a_tracker(sample_pack, tmp_path):
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "exercise_pack.json").write_text(json.dumps(sample_pack), encoding="utf-8")
    result = run_report(root=tmp_path, demo=True)
    out = Path(result["out"])
    assert out == tmp_path / "out" / "report_demo"
    for name in ("score.json", "after_action_report.docx", "executive_summary.pptx", "executive_summary.docx", "demo_tracker.xlsx"):
        assert (out / name).exists(), name
    assert json.loads((out / "score.json").read_text(encoding="utf-8"))["demo"]["label"]
    aar = Document(str(out / "after_action_report.docx"))
    assert "DEMO: SYNTHETIC RESPONSES" in "\n".join(p.text for t in aar.tables for r in t.rows for p in r.cells[0].paragraphs)
    deck = Presentation(str(out / "executive_summary.pptx"))
    for slide in deck.slides:
        assert any("DEMO: SYNTHETIC RESPONSES" in (sh.text_frame.text if sh.has_text_frame else "") for sh in slide.shapes)
    assert result["worked"] and result["improve"]
    # a real report must never pick up the demo tracker
    with pytest.raises(FileNotFoundError):
        find_tracker(sample_pack, root=tmp_path)


def test_report_demo_falls_back_to_the_sample_exercise(tmp_path):
    result = run_report(root=tmp_path, demo=True)
    assert result["notes"] and "sample exercise" in result["notes"][0]
    assert Path(result["out"]).parent == tmp_path / "out"


def test_lessons_learned_come_from_the_score(sample_pack):
    from ttx.build.exec_summary import lessons

    score = score_tracker(sample_pack, "samples/outputs/decision_tracker_completed.xlsx")
    worked, improve = lessons(sample_pack, score)
    assert 1 <= len(worked) <= 3 and 1 <= len(improve) <= 5
    assert any("silent on ransom payment" in i for i in improve)  # the plan gap the sample exercised
    for f in sample_pack["seed"]["findings_cited"]:
        assert f not in " ".join(worked + improve)
