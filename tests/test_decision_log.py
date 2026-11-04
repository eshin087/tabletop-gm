"""Live GM mode: the append-only decision log, its export, and the AAR timeline. No network, no model."""

from __future__ import annotations

import copy
import csv
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from docx import Document

from ttx.build.aar import build_aar
from ttx.common import read_json, read_yaml, write_json
from ttx.decision_log import (
    LogError, add_clocks, add_decision, add_mark, add_note, clock_rows, edit_decision, export, latest_decisions, load_log, start, timeline,
)
from ttx.score_engine import DIMENSIONS, score_tracker

REPO = Path(__file__).resolve().parent.parent
PACK = "samples/exercise_pack_sample.json"
LIVE = REPO / "samples" / "live"
T0 = "2026-11-06T17:00:00+00:00"


def _t(hhmm: str) -> str:
    return f"2026-11-06T{hhmm}:00+00:00"


def _docx_text(path):
    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            parts.extend(c.text for c in row.cells)
    return "\n".join(parts)


def _started(tmp_path, pack_path=PACK):
    return start(pack_path, tmp_path, "Test facilitator", now=T0)


# --------------------------------------------------------------------------- #
# log start
# --------------------------------------------------------------------------- #

def test_start_refuses_an_unapproved_pack(sample_pack, tmp_path):
    pack = copy.deepcopy(sample_pack)
    pack["approval"] = {"approved": False, "approved_by": None, "approved_at": None, "outline_hash": None}
    write_json(tmp_path / "draft.json", pack)
    with pytest.raises(LogError, match="not approved"):
        start(tmp_path / "draft.json", tmp_path / "live", "Test facilitator")
    assert not (tmp_path / "live" / "decision_log.json").exists()


def test_start_refuses_a_tampered_approval_hash(sample_pack, tmp_path):
    pack = copy.deepcopy(sample_pack)
    pack["injects"][0]["decision_owner_role"] = "ceo"  # changed after approval
    write_json(tmp_path / "tampered.json", pack)
    with pytest.raises(LogError, match="changed after approval"):
        start(tmp_path / "tampered.json", tmp_path / "live", "Test facilitator")


def test_start_refuses_an_existing_log_unless_resumed(tmp_path):
    log = _started(tmp_path)
    assert log["approval_hash"] == read_json(PACK)["approval"]["outline_hash"]
    with pytest.raises(LogError, match="--resume"):
        start(PACK, tmp_path, "Test facilitator", now=_t("17:05"))
    resumed = start(PACK, tmp_path, "Test facilitator", resume=True, now=_t("17:05"))
    assert resumed["resumed_at"] == [_t("17:05")]
    assert resumed["entries"][-1]["type"] == "note"


# --------------------------------------------------------------------------- #
# log add
# --------------------------------------------------------------------------- #

def test_add_refuses_unknown_inject_role_and_action(sample_pack, tmp_path):
    log = _started(tmp_path)
    with pytest.raises(LogError, match="unknown inject id"):
        add_decision(log, sample_pack, "I99", "x", "ceo", now=_t("17:01"))
    with pytest.raises(LogError, match="unknown role id"):
        add_decision(log, sample_pack, "I1", "x", "janitor", now=_t("17:01"))
    with pytest.raises(LogError, match="unknown action id"):
        add_decision(log, sample_pack, "I1", "x", "ceo", actions="I1-P16,I7-P42", now=_t("17:01"))
    with pytest.raises(LogError, match="unknown notified party"):
        add_decision(log, sample_pack, "I1", "x", "ceo", notified="the_press", now=_t("17:01"))
    with pytest.raises(LogError, match="--by other needs --note"):
        add_decision(log, sample_pack, "I1", "x", "other", now=_t("17:01"))
    assert log["entries"] == []  # every refusal left the log untouched


def test_add_computes_discussion_minutes_from_the_engine_clock(sample_pack, tmp_path):
    log = _started(tmp_path)
    add_mark(log, sample_pack, "I1", "presented", now=_t("17:04"))
    e = add_decision(log, sample_pack, "I1", "Called the IC", "security_operations", now=_t("17:11"))
    assert e["discussion_minutes"] == 7.0  # since the previous entry, not the session start
    assert e["at"] == _t("17:11") and e["n"] == 2 and e["unplanned"] is False
    outsider = add_decision(log, sample_pack, "I1", "Vendor shut it down", "other", unplanned=True, note="the vendor", now=_t("17:12"))
    assert outsider["unplanned"] and outsider["decided_by_role"] == "other"
    assert list(latest_decisions(log)) == ["I1"] and latest_decisions(log)["I1"] is e


def test_clocks_refuse_unknown_ids_and_later_answers_override(sample_pack, tmp_path):
    log = _started(tmp_path)
    with pytest.raises(LogError, match="unknown clock id"):
        add_clocks(log, sample_pack, owners={"gdpr_72h": "ceo"}, now=_t("17:01"))
    with pytest.raises(LogError, match="unknown role id"):
        add_clocks(log, sample_pack, owners={"hipaa_media_notice": "janitor"}, now=_t("17:01"))
    add_clocks(log, sample_pack, planned_hours={"hipaa_media_notice": 1500}, now=_t("17:02"))
    add_clocks(log, sample_pack, owners={"hipaa_media_notice": "communications"}, planned_hours={"hipaa_media_notice": 900}, now=_t("17:03"))
    rows = {r["clock_id"]: r for r in clock_rows(log, sample_pack)}
    assert rows["hipaa_media_notice"]["owner_role"] == "communications"
    assert rows["hipaa_media_notice"]["planned_notify_hours"] == 900.0
    assert rows["hipaa_individual_notice"]["internal_deadline_hours"] == 1080  # prefilled from the org plan, like the tracker


# --------------------------------------------------------------------------- #
# log edit
# --------------------------------------------------------------------------- #

def test_edit_keeps_the_original_and_export_uses_the_edited_version(sample_pack, tmp_path):
    log = _started(tmp_path)
    original = add_decision(log, sample_pack, "I1", "Parked it", "cfo", documented="no", now=_t("17:10"))
    with pytest.raises(LogError, match="only decision entries"):
        edit_decision(log, sample_pack, add_note(log, "break", now=_t("17:11"))["n"], "Host", {"decision": "x"}, now=_t("17:12"))
    corrected = edit_decision(log, sample_pack, original["n"], "Host",
                              {"decision": "Escalated to the IC", "decided_by_role": "security_operations", "documented": "yes"}, now=_t("17:30"))
    assert len(log["entries"]) == 3  # nothing destroyed
    assert original["superseded_by"] == corrected["n"]
    assert original["decision"] == "Parked it" and original["decided_by_role"] == "cfo"
    assert corrected["supersedes"] == original["n"] and corrected["edited_by"] == "Host" and corrected["edited_at"] == _t("17:30")
    assert corrected["at"] == original["at"]  # the timeline keeps the real decision time
    with pytest.raises(LogError, match="already corrected"):
        edit_decision(log, sample_pack, original["n"], "Host", {"decision": "again"}, now=_t("17:31"))
    with pytest.raises(LogError, match="unknown role id"):
        edit_decision(log, sample_pack, corrected["n"], "Host", {"decided_by_role": "janitor"}, now=_t("17:31"))

    paths = export(log, sample_pack, tmp_path)
    with open(paths["decisions"], encoding="utf-8", newline="") as fh:
        rows = {r["inject_id"]: r for r in csv.DictReader(fh)}
    assert rows["I1"]["decision"] == "Escalated to the IC"
    assert rows["I1"]["decided_by_role"] == "security_operations" and rows["I1"]["documented"] == "yes"
    assert len(rows) == len(sample_pack["injects"])  # one row per inject, unreached ones blank
    assert rows["I7"]["decision"] == "" and rows["I7"]["expected_owner"] == "ceo"


# --------------------------------------------------------------------------- #
# the scripted teams
# --------------------------------------------------------------------------- #

def _make_live_logs():
    spec = importlib.util.spec_from_file_location("make_live_logs", REPO / "samples" / "make_live_logs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_committed_scripted_logs_match_the_generator(tmp_path):
    built = _make_live_logs().build_logs(tmp_path)
    for name, path in built.items():
        committed = (LIVE / name / "decision_log.json").read_bytes()
        assert path.read_bytes() == committed, f"samples/live/{name}/decision_log.json is stale; run python samples/make_live_logs.py"


def _score_log(name, sample_pack, tmp_path):
    log = load_log(LIVE / name)
    out = tmp_path / name
    paths = export(log, sample_pack, out)
    return score_tracker(sample_pack, paths["decisions"]), log


def test_good_team_beats_poor_team_on_every_dimension_and_poor_misses_a_clock(sample_pack, tmp_path):
    good, good_log = _score_log("good", sample_pack, tmp_path)
    poor, poor_log = _score_log("poor", sample_pack, tmp_path)
    for dim in DIMENSIONS:
        g, p = good["summary"]["dimension_averages"][dim], poor["summary"]["dimension_averages"][dim]
        assert g is not None and p is not None, dim
        assert g > p, f"{dim}: good {g} vs poor {p}"
    assert good["summary"]["percent"] > poor["summary"]["percent"]
    assert good["summary"]["injects_scored"] == len(sample_pack["injects"])
    assert poor["summary"]["injects_scored"] == len(sample_pack["injects"]) - 1  # I5 was skipped
    assert not [c for c in good["clocks"] if c["status"] in {"missed", "not_planned"}]
    missed = [c["clock_id"] for c in poor["clocks"] if c["status"] == "missed"]
    assert "hipaa_media_notice" in missed
    assert [c for c in poor["clocks"] if c["status"] == "not_planned"]
    # unplanned entries exist in both logs and never reach the score
    assert any(e.get("unplanned") for e in good_log["entries"]) and any(e.get("unplanned") for e in poor_log["entries"])
    unplanned_text = next(e["decision"] for e in poor_log["entries"] if e.get("unplanned"))
    assert unplanned_text not in json.dumps(poor)


def test_scoring_the_same_exported_log_twice_is_byte_identical(sample_pack, tmp_path):
    log = load_log(LIVE / "good")
    a = export(log, sample_pack, tmp_path / "a")
    b = export(log, sample_pack, tmp_path / "b")
    assert Path(a["decisions"]).read_bytes() == Path(b["decisions"]).read_bytes()
    assert Path(a["clocks"]).read_bytes() == Path(b["clocks"]).read_bytes()
    write_json(tmp_path / "score1.json", score_tracker(sample_pack, a["decisions"]))
    write_json(tmp_path / "score2.json", score_tracker(copy.deepcopy(sample_pack), a["decisions"]))
    assert (tmp_path / "score1.json").read_bytes() == (tmp_path / "score2.json").read_bytes()


def test_export_columns_match_the_tracker_schema(sample_pack, tmp_path):
    doc = read_yaml(REPO / "schemas" / "tracker_columns.yaml")
    paths = export(load_log(LIVE / "good"), sample_pack, tmp_path)
    with open(paths["decisions"], encoding="utf-8", newline="") as fh:
        assert next(csv.reader(fh)) == doc["decisions"]
    with open(paths["clocks"], encoding="utf-8", newline="") as fh:
        assert next(csv.reader(fh)) == doc["clocks"]


# --------------------------------------------------------------------------- #
# aar --log
# --------------------------------------------------------------------------- #

def test_aar_log_appendix_lists_unplanned_entries_skips_notes_and_corrections(sample_pack, tmp_path):
    for name in ("good", "poor"):
        log = load_log(LIVE / name)
        paths = export(log, sample_pack, tmp_path / name)
        score = score_tracker(sample_pack, paths["decisions"])
        path = build_aar(sample_pack, score, tmp_path / f"{name}.docx", log=log, log_file=f"samples/live/{name}/decision_log.json")
        text = _docx_text(path)
        assert "Appendix: decision timeline" in text
        assert log["facilitator"] in text and f"samples/live/{name}/decision_log.json" in text
        for e in log["entries"]:
            if e["type"] == "decision":
                assert e["decision"] in text
            elif e["type"] == "note":
                assert e["text"] in text
        rows = timeline(log, sample_pack, score)
        assert any("[unplanned]" in r["entry"] and r["score"] == "not scored (unplanned)" for r in rows)
        assert any(r["score"] and "/" in r["score"] for r in rows)  # planned decisions carry their score
        assert "—" not in text
    poor_text = _docx_text(tmp_path / "poor.docx")
    assert "Inject I5 skipped by the host" in poor_text
    good_text = _docx_text(tmp_path / "good.docx")
    assert "superseded by entry" in good_text and "corrects entry 4, by Host" in good_text
    # without --log the report is unchanged
    plain = build_aar(sample_pack, read_json("samples/outputs/score.json"), tmp_path / "plain.docx")
    assert "Appendix: decision timeline" not in _docx_text(plain)


# --------------------------------------------------------------------------- #
# the CLI wiring
# --------------------------------------------------------------------------- #

def _run(*args):
    env = dict(os.environ)
    env.pop("TENABLE_ACCESS_KEY", None)
    env.pop("TENABLE_SECRET_KEY", None)
    return subprocess.run([sys.executable, "-m", "ttx.cli", *args], cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8")


def test_log_commands_from_the_cli(tmp_path):
    out = str(tmp_path / "live")
    r = _run("log", "start", "--pack", PACK, "--out", out, "--by", "CLI facilitator")
    assert r.returncode == 0, r.stdout + r.stderr
    r = _run("log", "start", "--pack", PACK, "--out", out, "--by", "CLI facilitator")
    assert r.returncode == 2 and "--resume" in r.stderr
    r = _run("log", "mark", "--out", out, "--inject", "I1", "--event", "presented")
    assert r.returncode == 0, r.stderr
    r = _run("log", "add", "--out", out, "--inject", "I1", "--decision", "Called the Incident Commander", "--by", "security_operations",
             "--actions", "I1-P16,I1-d1", "--plan-step", "yes", "--documented", "yes", "--scenario-minutes", "12")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["actions_completed"] == ["I1-P16", "I1-d1"]
    r = _run("log", "add", "--out", out, "--inject", "I9", "--decision", "x", "--by", "ceo")
    assert r.returncode == 2 and "unknown inject id" in r.stderr
    r = _run("log", "add", "--out", out, "--inject", "I2", "--decision", "Reset every password", "--by", "cio", "--unplanned")
    assert r.returncode == 0, r.stderr
    r = _run("log", "note", "--out", out, "--text", "Short break")
    assert r.returncode == 0, r.stderr
    r = _run("log", "clocks", "--out", out, "--owner", "hipaa_media_notice=communications", "--planned-hours", "hipaa_media_notice=1000")
    assert r.returncode == 0, r.stderr
    r = _run("log", "edit", "--out", out, "--entry", "2", "--by", "Host", "--decision", "Called the Incident Commander within 8 minutes")
    assert r.returncode == 0, r.stderr
    r = _run("log", "show", "--out", out)
    assert r.returncode == 0 and "superseded by #" in r.stdout and "[unplanned]" in r.stdout
    r = _run("log", "export", "--out", out)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "live" / "decisions.csv").exists() and (tmp_path / "live" / "decisions_clocks.csv").exists()
    r = _run("score", "--pack", PACK, "--tracker", str(tmp_path / "live" / "decisions.csv"), "--out", str(tmp_path / "score.json"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "injects scored 1/7" in r.stdout
    r = _run("aar", "--pack", PACK, "--score", str(tmp_path / "score.json"), "--log", str(tmp_path / "live" / "decision_log.json"),
             "--out", str(tmp_path / "aar.docx"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Called the Incident Commander within 8 minutes" in _docx_text(tmp_path / "aar.docx")
    log = read_json(tmp_path / "live" / "decision_log.json")
    assert [e["type"] for e in log["entries"]] == ["mark", "decision", "decision", "note", "clocks", "decision"]
