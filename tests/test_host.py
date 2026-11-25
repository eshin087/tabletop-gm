"""The host console: session, fact check, co-host, server routes, and the standalone page. No network, no model.

The co-host is exercised through a stand-in client, so these tests run without
the optional ``anthropic`` package and never open a socket.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from ttx.common import read_json, sha256_file
from ttx.decision_log import LogError, export
from ttx.host import cohost as ch
from ttx.host import conduct
from ttx.host.console import build_host_console, render_console
from ttx.host.server import App, make_handler
from ttx.host.session import END_NOTE, HostSession
from ttx.score_engine import score_tracker

REPO = Path(__file__).resolve().parent.parent
PACK = "samples/exercise_pack_sample.json"
GOOD_LOG = REPO / "samples" / "live" / "good" / "decision_log.json"
TOKEN = "test-token"
AUTH = {"X-TTX-Token": TOKEN}


def _app(tmp_path, cohost=None, **kwargs) -> App:
    session = HostSession(PACK, tmp_path / "host", "Test host")
    return App(session, cohost=cohost, cohost_reason="no key in this test", token=TOKEN, opener=lambda path: True, **kwargs)


def _call(app: App, method: str, path: str, data: dict | None = None, headers: dict | None = AUTH):
    response = app.handle(method, path, json.dumps(data or {}).encode("utf-8"), headers or {})
    body = json.loads(response.body) if response.body and response.content_type.startswith("application/json") else response.body
    return response.status, body


def _sse(response) -> list[tuple[str, dict]]:
    events = []
    for block in b"".join(response.stream).decode("utf-8").strip().split("\n\n"):
        name = next(line[7:] for line in block.split("\n") if line.startswith("event: "))
        data = next(line[6:] for line in block.split("\n") if line.startswith("data: "))
        events.append((name, json.loads(data)))
    return events


# --------------------------------------------------------------------------- #
# The fact check
# --------------------------------------------------------------------------- #

def test_conduct_passes_text_built_from_pack_facts(sample_pack):
    text = "Attackers reached sql2016 through vpngw01 (CVE-2025-0282, VPR 9.6). The state report is due in 15 business days."
    assert conduct.check_text(text, sample_pack, current_index=5) == []


def test_conduct_accepts_a_pack_deadline_said_in_another_unit(sample_pack):
    # the HIPAA clocks are stored as 1440 hours; "60 days" and "sixty days" are the same fact
    assert conduct.check_text("The HIPAA notices are due within 60 days.", sample_pack, 5) == []
    assert conduct.check_text("That is sixty days from discovery.", sample_pack, 5) == []


def test_conduct_flags_an_invented_deadline_and_an_invented_system(sample_pack):
    findings = conduct.check_text("You have 48 hours to tell the regulator, and srv-db07 lost 3,200 records.", sample_pack, 5)
    assert {"kind": "time_claim", "token": "48 hours"} in findings
    assert {f["token"] for f in findings if f["kind"] == "unknown_number"} == {"srv-db07", "3200"}


def test_conduct_flags_a_deadline_written_in_words(sample_pack):
    findings = conduct.check_text("The board wants an answer within seventy-two hours.", sample_pack, 3)
    assert [f["kind"] for f in findings] == ["time_claim"]


def test_conduct_flags_text_from_an_inject_the_room_has_not_reached(sample_pack):
    later = sample_pack["injects"][6]["what_happens"]
    assert any(f["kind"] == "spoiler" for f in conduct.check_text(later, sample_pack, current_index=2))
    assert not any(f["kind"] == "spoiler" for f in conduct.check_text(later, sample_pack, current_index=6))


def test_conduct_flags_an_expected_answer_even_for_the_current_inject(sample_pack):
    good = sample_pack["injects"][0]["what_good_looks_like"]
    assert any(f["kind"] == "spoiler" for f in conduct.check_text(good, sample_pack, current_index=0))


def test_conduct_lets_the_room_keep_its_own_numbers(sample_pack):
    room = "We would notify within 5 days and expect 12 workstations affected."
    line = "Noted: 12 workstations. Who owns that notice?"
    assert conduct.check_text(line, sample_pack, 3, extra=room) == []
    assert conduct.check_text("Noted: 14 workstations.", sample_pack, 3, extra=room)[0]["token"] == "14"


# --------------------------------------------------------------------------- #
# Session and routes: every change is one decision_log call
# --------------------------------------------------------------------------- #

def test_page_is_served_with_the_pack_and_no_placeholder(tmp_path):
    app = _app(tmp_path)
    response = app.handle("GET", "/", b"", {})
    page = response.body.decode("utf-8")
    assert response.status == 200 and response.content_type.startswith("text/html")
    assert "__TTX_BOOT__" not in page
    assert "Valley Regional Health System" in page and TOKEN in page


def test_api_refuses_a_call_without_the_session_token(tmp_path):
    app = _app(tmp_path)
    assert _call(app, "POST", "/api/present", {"inject_id": "I1"}, headers={})[0] == 403
    assert _call(app, "POST", "/api/present", {"inject_id": "I1"}, headers={"X-TTX-Token": "wrong"})[0] == 403
    assert app.session.log()["entries"] == []


def test_capture_goes_through_the_engine_and_refuses_unknown_ids(tmp_path):
    app = _app(tmp_path)
    assert _call(app, "POST", "/api/present", {"inject_id": "I1"})[0] == 200
    status, body = _call(app, "POST", "/api/decision", {"inject_id": "I1", "decision": "Called the IC.", "by": "nobody"})
    assert status == 409 and "unknown role id" in body["error"]
    status, body = _call(app, "POST", "/api/decision", {"inject_id": "I1", "decision": "Called the IC.", "by": "security_operations", "actions": ["I9-x"]})
    assert status == 409 and "unknown action id" in body["error"]
    status, body = _call(app, "POST", "/api/decision", {
        "inject_id": "I1", "decision": "Treated it as a suspected SEV1 and called the Incident Commander.", "by": "security_operations",
        "actions": ["I1-P16", "I1-d1"], "plan_step": "yes", "documented": "partial", "scenario_minutes": "10"})
    assert status == 200
    entries = body["log"]["entries"]
    assert [e["type"] for e in entries] == ["mark", "decision"]
    assert entries[1]["actions_completed"] == ["I1-P16", "I1-d1"] and entries[1]["scenario_minutes"] == 10.0
    assert _call(app, "POST", "/api/clocks", {"owners": {"hipaa_media_notice": "communications"}, "planned_hours": {"hipaa_media_notice": 100}})[0] == 200
    assert _call(app, "POST", "/api/clocks", {"owners": {"no_such_clock": "ceo"}})[0] == 409
    assert _call(app, "POST", "/api/skip", {"inject_id": "I2"})[0] == 200
    assert _call(app, "POST", "/api/note", {"text": "Paused"})[0] == 200
    assert _call(app, "GET", "/api/state")[1]["log"]["entries"][-1]["text"] == "Paused"
    assert _call(app, "POST", "/api/nope")[0] == 404


def test_a_restarted_server_resumes_from_the_log(tmp_path):
    app = _app(tmp_path)
    _call(app, "POST", "/api/present", {"inject_id": "I1"})
    with pytest.raises(LogError, match="already exists"):
        HostSession(PACK, tmp_path / "host", "Test host")
    again = HostSession(PACK, tmp_path / "host", "Test host", resume=True)
    assert [e["type"] for e in again.log()["entries"]] == ["mark", "note"]


def test_end_scores_with_the_same_engine_as_ttx_report(tmp_path):
    app = _app(tmp_path)
    _call(app, "POST", "/api/present", {"inject_id": "I1"})
    _call(app, "POST", "/api/decision", {"inject_id": "I1", "decision": "Called the Incident Commander.", "by": "security_operations",
                                           "actions": ["I1-P16"], "plan_step": "yes", "documented": "yes"})
    status, body = _call(app, "POST", "/api/end")
    assert status == 200 and body["ended"] is True
    report = body["report"]
    out = tmp_path / "host"
    for name in ("score.json", "after_action_report.docx", "executive_summary.pptx", "executive_summary.docx", "decisions.csv"):
        assert (out / name).exists(), name
    log = read_json(out / "decision_log.json")
    assert log["entries"][-1] == {**log["entries"][-1], "type": "note", "text": END_NOTE}
    again = score_tracker(app.session.pack, export(log, app.session.pack, tmp_path / "again")["decisions"])
    assert report["summary"]["percent"] == again["summary"]["percent"]
    assert report["rating"] in ("Strong", "Adequate", "Needs work")
    # after the end the record is closed
    status, body = _call(app, "POST", "/api/present", {"inject_id": "I2"})
    assert status == 409 and "ended" in body["error"]
    assert _call(app, "POST", "/api/open", {"what": "after_action_report"})[1]["opened"] is True
    assert _call(app, "POST", "/api/open", {"what": "../secrets"})[0] == 400


def test_replay_is_read_only_and_leaves_the_recording_untouched(tmp_path):
    before = sha256_file(GOOD_LOG)
    session = HostSession.replay(GOOD_LOG, tmp_path / "replay", PACK)
    app = App(session, replay=True, token=TOKEN)
    assert app.boot()["server"]["mode"] == "replay"
    status, body = _call(app, "POST", "/api/present", {"inject_id": "I1"})
    assert status == 409 and "replay" in body["error"]
    assert _call(app, "POST", "/api/cohost/voice", {"inject_id": "I1", "mode": "present"})[0] == 409
    status, body = _call(app, "POST", "/api/end")
    assert status == 200 and body["report"]["summary"]["injects_scored"] == 7
    assert len(read_json(tmp_path / "replay" / "decision_log.json")["entries"]) == len(read_json(GOOD_LOG)["entries"])
    assert sha256_file(GOOD_LOG) == before


# --------------------------------------------------------------------------- #
# The co-host, through a stand-in client
# --------------------------------------------------------------------------- #

class _Stream:
    def __init__(self, chunks, stop_reason):
        self.text_stream = iter(chunks)
        self._final = SimpleNamespace(stop_reason=stop_reason, usage=SimpleNamespace(input_tokens=900, output_tokens=40,
                                                                                    cache_read_input_tokens=700, cache_creation_input_tokens=0))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self._final


class _Messages:
    def __init__(self, answer=None, chunks=("Logged. ", "Who owns the notice?"), stop_reason="end_turn"):
        self.answer, self.chunks, self.stop_reason, self.calls = answer or {}, chunks, stop_reason, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(stop_reason=self.stop_reason, content=[SimpleNamespace(type="text", text=json.dumps(self.answer))],
                               usage=SimpleNamespace(input_tokens=1000, output_tokens=50, cache_read_input_tokens=0, cache_creation_input_tokens=0))

    def stream(self, **kwargs):
        self.calls.append(kwargs)
        return _Stream(self.chunks, self.stop_reason)


def _cohost(**kwargs) -> tuple[ch.AnthropicCohost, _Messages]:
    messages = _Messages(**kwargs)
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return ch.AnthropicCohost(client=client, model="claude-opus-5-5", effort="low", fast=False), messages


def test_suggestion_schema_offers_only_ids_the_pack_defines(sample_pack):
    inject = sample_pack["injects"][0]
    schema = ch.suggest_schema(sample_pack, inject)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["actions_completed"]["items"]["enum"] == [a["id"] for a in inject["expected_actions"]]
    assert set(schema["properties"]["decided_by_role"]["enum"]) == {r["id"] for r in sample_pack["roles"]} | {"other", "unclear"}
    assert schema["properties"]["ask_next"]["enum"] == inject["probing_questions"] + [""]


def test_suggest_keeps_only_known_ids_and_sends_the_documented_request(sample_pack):
    inject = sample_pack["injects"][0]
    answer = {"decision": "Paged the Incident Commander.", "decided_by_role": "security_operations", "actions_completed": ["I1-P16", "I7-fake"],
              "notified": ["made_up_party"], "plan_step_followed": "unclear", "documented": "yes", "unplanned": False, "ask_next": "An invented question?"}
    cohost, messages = _cohost(answer=answer)
    got = cohost.suggest(sample_pack, inject, "The analyst paged the IC.")
    assert got["actions_completed"] == ["I1-P16"] and got["notified"] == []
    assert got["plan_step_followed"] is None and got["documented"] == "yes" and got["ask_next"] == ""
    sent = messages.calls[0]
    assert sent["model"] == "claude-opus-5-5" and sent["fallbacks"] == "default" and sent["betas"] == [ch.FALLBACK_BETA]
    assert sent["output_config"]["effort"] == "low" and sent["output_config"]["format"]["type"] == "json_schema"
    assert sent["system"][-1]["cache_control"] == {"type": "ephemeral"} and "speed" not in sent
    assert cohost.info()["usage"]["calls"] == 1 and cohost.info()["estimated_cost_usd"] == pytest.approx(0.005)


def test_voice_never_receives_a_later_inject_or_an_expected_answer(sample_pack):
    cohost, messages = _cohost()
    inject = sample_pack["injects"][2]
    assert "".join(cohost.voice(sample_pack, inject, "react", room_text="We isolate now.", earlier=[])) == "Logged. Who owns the notice?"
    sent = json.dumps(messages.calls[0]["messages"]) + json.dumps(messages.calls[0]["system"])
    assert inject["what_happens"][:40] in sent
    assert inject["what_good_looks_like"][:40] not in sent and inject["where_teams_fail"][:40] not in sent
    for later in sample_pack["injects"][3:]:
        assert later["title"] not in sent and later["what_happens"][:40] not in sent


def test_a_declined_request_becomes_a_plain_error_not_a_line(sample_pack):
    cohost, _ = _cohost(stop_reason="refusal", chunks=("Partial text that must not be used",))
    with pytest.raises(ch.CohostError, match="declined"):
        list(cohost.voice(sample_pack, sample_pack["injects"][0], "present"))
    with pytest.raises(ch.CohostError, match="declined"):
        cohost.suggest(sample_pack, sample_pack["injects"][0], "anything")


def test_voice_route_streams_the_line_then_its_fact_check(tmp_path):
    cohost, _ = _cohost(chunks=("Logged. ", "You have 48 hours to tell the regulator."))
    app = _app(tmp_path, cohost=cohost)
    response = app.handle("POST", "/api/cohost/voice", json.dumps({"inject_id": "I1", "mode": "react", "text": "We call the IC."}).encode(), AUTH)
    events = _sse(response)
    assert [name for name, _ in events] == ["delta", "delta", "done"]
    assert events[-1][1]["findings"] == [{"kind": "time_claim", "token": "48 hours"}]
    info = app.server_info()["ai"]
    assert info["enabled"] is True and info["lines_checked"] == 1 and info["lines_flagged"] == 1


def test_voice_route_reports_a_decline_as_an_error_event(tmp_path):
    cohost, _ = _cohost(stop_reason="refusal")
    app = _app(tmp_path, cohost=cohost)
    response = app.handle("POST", "/api/cohost/voice", json.dumps({"inject_id": "I1", "mode": "present"}).encode(), AUTH)
    assert _sse(response)[-1][0] == "error"


def test_suggest_route_needs_text_and_a_cohost(tmp_path):
    assert _call(_app(tmp_path), "POST", "/api/cohost/suggest", {"inject_id": "I1", "text": "x"})[0] == 409
    cohost, _ = _cohost(answer={"decision": "Paged the IC.", "decided_by_role": "security_operations"})
    app = App(HostSession(PACK, tmp_path / "second", "Test host"), cohost=cohost, token=TOKEN)
    assert _call(app, "POST", "/api/cohost/suggest", {"inject_id": "I1", "text": ""})[0] == 400
    status, body = _call(app, "POST", "/api/cohost/suggest", {"inject_id": "I1", "text": "The analyst paged the IC."})
    assert status == 200 and body["suggestion"]["decided_by_role"] == "security_operations"


def test_cohost_is_off_without_a_key_or_when_switched_off():
    assert ch.make_cohost({})[0] is None and "ANTHROPIC_API_KEY" in ch.make_cohost({})[1]
    assert ch.make_cohost({"ANTHROPIC_API_KEY": "x", "TTX_HOST_AI": "off"})[0] is None


def test_cost_estimate_uses_list_prices_and_doubles_in_fast_mode():
    usage = {"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 1_000_000, "cache_creation_input_tokens": 0}
    assert ch.estimate_cost(usage, "claude-opus-5-5") == pytest.approx(6.2)
    assert ch.estimate_cost(usage, "claude-opus-5-5", fast=True) == pytest.approx(12.4)
    assert ch.estimate_cost(usage, "some-other-model") is None


# --------------------------------------------------------------------------- #
# The HTTP layer, driven through an in-memory socket
# --------------------------------------------------------------------------- #

class _Sock:
    def __init__(self, request: bytes):
        self._in, self.out = io.BytesIO(request), io.BytesIO()

    def makefile(self, mode, *args, **kwargs):
        return self._in

    def sendall(self, data):
        self.out.write(data)


def _http(app: App, raw: str) -> str:
    sock = _Sock(raw.replace("\n", "\r\n").encode("utf-8"))
    make_handler(app, {"127.0.0.1:8765", "localhost:8765"})(sock, ("127.0.0.1", 50000), None)
    return sock.out.getvalue().decode("utf-8", "replace")


def test_http_layer_only_answers_on_localhost(tmp_path):
    app = _app(tmp_path)
    assert _http(app, "GET / HTTP/1.1\nHost: evil.example:8765\n\n").startswith("HTTP/1.0 403")
    ok = _http(app, "GET / HTTP/1.1\nHost: localhost:8765\n\n")
    assert ok.startswith("HTTP/1.0 200") and "X-Content-Type-Options: nosniff" in ok and "Tabletop GM host console" in ok
    body = '{"inject_id": "I1"}'
    posted = _http(app, f"POST /api/present HTTP/1.1\nHost: 127.0.0.1:8765\nX-TTX-Token: {TOKEN}\nContent-Type: application/json\nContent-Length: {len(body)}\n\n{body}")
    assert posted.startswith("HTTP/1.0 200") and '"event": "presented"' in posted


def test_http_layer_streams_server_sent_events(tmp_path):
    cohost, _ = _cohost(chunks=("One. ", "Two."))
    app = _app(tmp_path, cohost=cohost)
    body = '{"inject_id": "I1", "mode": "present"}'
    out = _http(app, f"POST /api/cohost/voice HTTP/1.1\nHost: localhost:8765\nX-TTX-Token: {TOKEN}\nContent-Length: {len(body)}\n\n{body}")
    assert "text/event-stream" in out and out.count("event: delta") == 2 and "event: done" in out


# --------------------------------------------------------------------------- #
# host.html and the command line
# --------------------------------------------------------------------------- #

def test_console_page_is_self_contained():
    for name in ("console.html", "room.html"):
        template = (REPO / "ttx" / "host" / name).read_text(encoding="utf-8")
        for needle in ("http://", "https://", "<link", " src=", "@import", "url("):
            assert needle not in template, f"{name} must not load anything from the network: found {needle!r}"


def test_build_writes_a_standalone_host_console(sample_pack, tmp_path):
    from ttx.build import build_all

    built = build_all(sample_pack, tmp_path / "out", only=["host"])
    page = Path(built["host_console"]).read_text(encoding="utf-8")
    assert Path(built["host_console"]).name == "host.html"
    assert '"served": false' in page and "__TTX_BOOT__" not in page
    boot = json.loads(page.split('<script id="boot" type="application/json">', 1)[1].split("</script>", 1)[0])
    assert boot["pack"]["approval"]["outline_hash"] == sample_pack["approval"]["outline_hash"]
    assert boot["token"] is None and boot["log"] is None


def test_page_data_cannot_break_out_of_its_script_block(sample_pack):
    pack = json.loads(json.dumps(sample_pack))
    pack["title"] = "</script><script>alert(1)</script>"
    page = render_console({"pack": pack, "log": None}, served=False)
    block = page.split('<script id="boot" type="application/json">', 1)[1].split("</script>", 1)[0]
    assert "<" not in block and json.loads(block)["pack"]["title"] == pack["title"]


def test_draft_console_is_marked_for_rehearsal_only(sample_pack, tmp_path):
    page = build_host_console(sample_pack, tmp_path / "host.html", draft=True).read_text(encoding="utf-8")
    assert '"draft": true' in page


def test_a_log_exported_by_host_html_is_scored_by_ttx_report(tmp_path):
    # tests/data/host_html_export.json was exported from the standalone page in a real browser (2026-11-23):
    # seven injects walked through with the keyboard, one skipped. It carries no pack path of its own.
    import shutil

    from ttx.decision_log import load_log, load_pack_for, show
    from ttx.report import run_report

    shutil.copyfile(REPO / "tests" / "data" / "host_html_export.json", tmp_path / "decision_log.json")
    log = load_log(tmp_path)
    assert log["generator"].startswith("Tabletop GM host.html")
    pack = load_pack_for(log, PACK)  # same approval hash, so the engine accepts it
    assert "skipped" in show(log, pack)
    result = run_report(pack_path=PACK, log_path=str(tmp_path / "decision_log.json"))
    assert result["summary"]["injects_scored"] == 6 and result["summary"]["injects_total"] == 7
    assert (tmp_path / "after_action_report.docx").exists() and (tmp_path / "executive_summary.pptx").exists()


def test_launcher_picks_the_first_unused_session_folder(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("launcher_under_test", REPO / "scripts" / "launcher.py")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    assert launcher.host_out_dir(tmp_path) == tmp_path / "out" / "host"
    HostSession(PACK, tmp_path / "out" / "host", "Test host")
    assert launcher.host_out_dir(tmp_path) == tmp_path / "out" / "host-2"


def test_host_command_refuses_a_missing_recording(tmp_path):
    r = subprocess.run([sys.executable, "-m", "ttx.cli", "host", "--replay", str(tmp_path / "missing.json"), "--no-open"],
                       cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 2 and "decision log not found" in r.stderr


def test_host_command_refuses_a_second_session_in_the_same_folder(tmp_path):
    HostSession(PACK, tmp_path / "host", "Test host")
    r = subprocess.run([sys.executable, "-m", "ttx.cli", "host", "--pack", PACK, "--out", str(tmp_path / "host"), "--no-open"],
                       cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 2 and "--resume" in r.stderr


# --------------------------------------------------------------------------- #
# The room screen: what the wall may and may not show
# --------------------------------------------------------------------------- #

def _room(app: App) -> dict:
    response = app.handle("GET", "/room/state", b"", {})
    assert response.status == 200
    return json.loads(response.body)


def _decide(app: App, inject_id: str, by: str):
    return _call(app, "POST", "/api/decision", {"inject_id": inject_id, "decision": f"Decision for {inject_id}.", "by": by})


def test_room_page_and_state_need_no_token_and_carry_no_pack(tmp_path, sample_pack):
    app = _app(tmp_path)
    page = app.handle("GET", "/room", b"", {})
    assert page.status == 200 and b"Tabletop GM room screen" in page.body
    assert TOKEN.encode() not in page.body and sample_pack["injects"][3]["title"].encode() not in page.body
    assert app.server_info()["room_open"] is False
    state = _room(app)
    assert state["inject"] is None and state["score"] is None and state["ground_rules"]
    assert app.server_info()["room_open"] is True


def test_room_never_shows_answers_deadlines_or_anything_not_yet_presented(tmp_path, sample_pack):
    app = _app(tmp_path)
    _call(app, "POST", "/api/present", {"inject_id": "I1"})
    blob = json.dumps(_room(app))
    first = sample_pack["injects"][0]
    assert first["title"] in blob and first["decision_forced"] in blob
    for inject in sample_pack["injects"]:
        assert inject["what_good_looks_like"] not in blob and inject["where_teams_fail"] not in blob
        assert (inject["procedure_tested"].get("quote") or "no quote") not in blob
        for action in inject["expected_actions"]:
            assert action["text"] not in blob
    for later in sample_pack["injects"][1:]:
        assert later["title"] not in blob and later["what_happens"] not in blob
    # the path shows only the system the story has reached; the others stay unnamed
    assert "vpngw01" in blob and "dc1" not in blob and "sql2016" not in blob
    for clock in sample_pack["clocks"]:
        assert clock["name"] not in blob and clock["id"] not in blob
    assert "deadline" not in blob and "percent" not in blob and "CVE-" not in blob


def test_room_path_advances_with_the_story(tmp_path):
    app = _app(tmp_path)
    _call(app, "POST", "/api/present", {"inject_id": "I1"})
    assert [(n["asset"], n["state"], n["since"]) for n in _room(app)["path"]] == [("vpngw01", "active", "T+0:10"), (None, "unknown", None), (None, "unknown", None)]
    _decide(app, "I1", "security_operations")
    # inject 2 cites the entry finding but tells the room the attacker is on dc1: the wall follows what the room was told
    _call(app, "POST", "/api/present", {"inject_id": "I2"})
    assert [(n["asset"], n["state"], n["since"]) for n in _room(app)["path"]] == [("vpngw01", "passed", "T+0:10"), ("dc1", "active", "T+0:20"), (None, "unknown", None)]
    _decide(app, "I2", "incident_commander")
    _call(app, "POST", "/api/present", {"inject_id": "I3"})
    path = _room(app)["path"]
    assert [(n["asset"], n["state"]) for n in path] == [("vpngw01", "passed"), ("dc1", "active"), (None, "unknown")]
    _decide(app, "I3", "incident_commander")
    _call(app, "POST", "/api/present", {"inject_id": "I4"})
    state = _room(app)
    assert [(n["asset"], n["state"]) for n in state["path"]][-1] == ("sql2016", "active")
    assert state["inject"]["n"] == 4 and state["logged"] is None
    assert any(f["text"] == "decision logged, inject 03, Incident Commander" for f in state["feed"])


def test_room_shows_the_logged_decision_and_the_score_only_after_the_end(tmp_path):
    app = _app(tmp_path)
    _call(app, "POST", "/api/present", {"inject_id": "I1"})
    _decide(app, "I1", "security_operations")
    state = _room(app)
    assert state["logged"]["by"] == "Director of Security Operations" and state["logged"]["decision"] == "Decision for I1."
    assert state["score"] is None and state["ended"] is False
    _call(app, "POST", "/api/end")
    state = _room(app)
    assert state["ended"] is True and state["score"]["rating"] in ("Strong", "Adequate", "Needs work")
    assert len(state["score"]["dimensions"]) == 5 and "gaps" not in state["score"]


def test_wall_waits_for_the_cohost_and_shows_only_a_line_that_passed_the_check(tmp_path, sample_pack):
    clean = "Your analyst sees a new administrator session on vpngw01."
    cohost, _ = _cohost(chunks=(clean,))
    app = _app(tmp_path, cohost=cohost)
    _call(app, "POST", "/api/present", {"inject_id": "I1"})
    assert _room(app)["line"] == {"text": "", "source": "ai", "writing": True, "checked": False}
    events = _sse(app.handle("POST", "/api/cohost/voice", json.dumps({"inject_id": "I1", "mode": "present", "wall": True}).encode(), AUTH))
    assert events[-1][1]["on_wall"] is True
    line = _room(app)["line"]
    assert line == {"text": clean, "source": "ai", "writing": False, "checked": True}
    assert any(f["text"] == "fact check passed" for f in _room(app)["feed"])


def test_a_flagged_ai_line_never_reaches_the_wall(tmp_path, sample_pack):
    invented = "You have 48 hours before srv-db07 goes public."
    cohost, _ = _cohost(chunks=(invented,))
    app = _app(tmp_path, cohost=cohost)
    _call(app, "POST", "/api/present", {"inject_id": "I1"})
    events = _sse(app.handle("POST", "/api/cohost/voice", json.dumps({"inject_id": "I1", "mode": "present", "wall": True}).encode(), AUTH))
    assert events[-1][1]["on_wall"] is False and events[-1][1]["findings"]
    state = _room(app)
    assert state["line"]["source"] == "script" and state["line"]["text"] == sample_pack["injects"][0]["host_lines"][0]
    assert invented not in json.dumps(state) and "48 hours" not in json.dumps(state)
    assert any("held back" in f["text"] for f in state["feed"])


def test_wall_falls_back_to_the_script_when_the_cohost_declines(tmp_path, sample_pack):
    cohost, _ = _cohost(stop_reason="refusal")
    app = _app(tmp_path, cohost=cohost)
    _call(app, "POST", "/api/present", {"inject_id": "I1"})
    _sse(app.handle("POST", "/api/cohost/voice", json.dumps({"inject_id": "I1", "mode": "present", "wall": True}).encode(), AUTH))
    assert _room(app)["line"]["text"] == sample_pack["injects"][0]["host_lines"][0]


def test_push_puts_a_script_follow_up_on_the_wall_without_a_cohost(tmp_path, sample_pack):
    app = _app(tmp_path)
    assert _call(app, "POST", "/api/wall/push", {"inject_id": "I1"})[0] == 409  # not presented yet
    _call(app, "POST", "/api/present", {"inject_id": "I1"})
    questions = sample_pack["injects"][0]["probing_questions"]
    status, body = _call(app, "POST", "/api/wall/push", {"inject_id": "I1"})
    assert status == 200 and body["stake"] == {"role": "Facilitator", "text": questions[0], "source": "script"}
    assert _room(app)["stake"]["text"] == questions[0]
    assert _call(app, "POST", "/api/wall/push", {"inject_id": "I1"})[1]["stake"]["text"] == questions[1 % len(questions)]
    # the next inject starts with a clean wall
    _decide(app, "I1", "security_operations")
    _call(app, "POST", "/api/present", {"inject_id": "I2"})
    assert _room(app)["stake"] is None


def test_push_lets_the_cohost_speak_only_as_a_role_the_pack_defines(tmp_path, sample_pack):
    good = 'Chief Executive Officer: "Who is making this call right now?"'
    cohost, messages = _cohost(chunks=(good,))
    app = _app(tmp_path, cohost=cohost)
    _call(app, "POST", "/api/present", {"inject_id": "I1"})
    status, body = _call(app, "POST", "/api/wall/push", {"inject_id": "I1"})
    assert status == 200 and body["stake"] == {"role": "Chief Executive Officer", "text": "Who is making this call right now?", "source": "ai"}
    sent = json.dumps(messages.calls[-1]["messages"])
    assert "stakeholder" in sent and sample_pack["injects"][1]["title"] not in sent
    assert _room(app)["stake"]["role"] == "Chief Executive Officer"
    for bad in ('Head of Rumors: "I heard the board is furious."', 'Chief Executive Officer: "You have 48 hours."', "Just some text"):
        cohost.client.beta.messages.chunks = (bad,)
        status, body = _call(app, "POST", "/api/wall/push", {"inject_id": "I1"})
        assert status == 200 and body["stake"]["source"] == "script" and body["stake"]["role"] == "Facilitator"
        assert "48 hours" not in json.dumps(_room(app)) and "Rumors" not in json.dumps(_room(app))


def test_cohost_request_matches_each_supported_model():
    from ttx.host.cohost import AnthropicCohost, estimate_cost

    pack = read_json(PACK)
    opus = AnthropicCohost(client=object(), model="claude-opus-5-5", fast=True)._request("r", pack, "u", 100)
    assert opus["fallbacks"] == "default" and opus["speed"] == "fast"
    sonnet = AnthropicCohost(client=object(), model="claude-sonnet-5-5", fast=True)
    req = sonnet._request("r", pack, "u", 100)
    assert req["fallbacks"] == "default" and "speed" not in req and sonnet.fast is False
    haiku = AnthropicCohost(client=object(), model="claude-haiku-5-5")._request("r", pack, "u", 100)
    assert "fallbacks" not in haiku and "betas" not in haiku and haiku["output_config"]["effort"] == "low"
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    assert estimate_cost(usage, "claude-sonnet-5-5") == 12.0 and estimate_cost(usage, "claude-haiku-5-5") == 0.6


def test_parse_stake_accepts_only_the_documented_form(sample_pack):
    from ttx.host.server import parse_stake

    assert parse_stake('chief financial officer: "Do I take the call?"', sample_pack) == {"role": "Chief Financial Officer", "text": "Do I take the call?"}
    assert parse_stake("Chief Financial Officer: Do I take the call?", sample_pack) is None
    assert parse_stake('The Attacker: "Pay up."', sample_pack) is None


def test_replay_drives_the_wall_from_its_cursor(tmp_path):
    session = HostSession.replay(GOOD_LOG, tmp_path / "replay", PACK)
    app = App(session, replay=True, token=TOKEN)
    assert _room(app)["inject"] is None and _room(app)["mode"] == "replay"
    assert _call(app, "POST", "/api/replay/cursor", {"n": 1})[1] == {"cursor": 1}
    assert _room(app)["inject"]["id"] == "I1" and _room(app)["logged"] is None
    assert _room(app)["as_of"] == _room(app)["inject"]["presented_at"]  # the wall timer reads recorded time in a replay
    assert _call(app, "POST", "/api/replay/cursor", {"n": 2})[0] == 200
    assert _room(app)["logged"]["by"] == "Director of Security Operations"
    total = len(read_json(GOOD_LOG)["entries"])
    _call(app, "POST", "/api/replay/cursor", {"n": 999})
    assert app.cursor == total and _room(app)["score"] is None
    assert app.server_info()["cursor"] == total  # a reloaded host console picks up where the replay is
    _call(app, "POST", "/api/end")
    assert _room(app)["score"]["decisions_scored"] == 7 and _room(app)["ended"] is True
    assert _call(app, "POST", "/api/wall/push", {"inject_id": "I1"})[0] == 409
    live = _app(tmp_path)
    assert _call(live, "POST", "/api/replay/cursor", {"n": 3})[0] == 409
