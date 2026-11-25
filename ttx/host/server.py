"""``ttx host``: the host console served from this machine. Standard library only.

Two pages. ``/`` is the host remote, private to the facilitator's laptop.
``/room`` is the room screen for the wall or projector; it is fed only by
``ttx.host.room.room_state``, which never contains an answer, a deadline, a
score before the end, or anything the facilitator has not presented yet.

The server binds to 127.0.0.1, checks the Host header, and requires a random
per-run token on every call that can change anything, so another page open in
the same browser cannot drive it. The record lives in the decision log: every
change is one ``HostSession`` method, which is one ``ttx.decision_log`` call.
The only thing held in memory is what is on the wall right now.

``App.handle`` is a plain function from a request to a response, so the tests
exercise every route without opening a socket.
"""

from __future__ import annotations

import json
import re
import secrets
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator

from .. import __version__
from ..common import now_iso
from ..decision_log import LogError
from . import conduct, room
from .cohost import CohostError
from .console import render_console, render_room
from .session import HostSession

OPENABLE = ("after_action_report", "executive_summary_slides", "executive_summary_memo", "score")
WRITING_TIMEOUT = 30  # seconds the wall waits for the co-host's line before it shows the script
_STAKE = re.compile(r"^\s*([^:\n]{2,80}):\s*[\"“](.+?)[\"”]\s*$", re.DOTALL)


@dataclass
class Response:
    status: int = 200
    content_type: str = "application/json; charset=utf-8"
    body: bytes = b""
    stream: Iterator[bytes] | None = None
    headers: dict[str, str] = field(default_factory=dict)


def _json(data: Any, status: int = 200) -> Response:
    return Response(status=status, body=json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"),
                    headers={"Cache-Control": "no-store"})


def _error(message: str, status: int = 400) -> Response:
    return _json({"error": message}, status)


def _sse(event: str, data: Any) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


def parse_stake(text: str, pack: dict) -> dict | None:
    """Read 'Role name: "line"' and keep it only when the role is one the pack defines."""
    m = _STAKE.match(text or "")
    if not m:
        return None
    said = m.group(1).strip().lower()
    for r in pack.get("roles", []):
        if (r.get("name") or "").lower() == said:
            return {"role": r["name"], "text": m.group(2).strip()}
    return None


class App:
    def __init__(self, session: HostSession, cohost: Any = None, cohost_reason: str = "", replay: bool = False,
                 token: str | None = None, opener=None):
        self.session = session
        self.cohost = cohost
        self.cohost_reason = cohost_reason
        self.replay = replay
        self.token = token or secrets.token_urlsafe(18)
        self.opener = opener
        self._corpus = conduct.Corpus(session.pack)
        self.flagged_lines = 0
        self.checked_lines = 0
        self._lock = threading.Lock()
        # what is on the wall right now; never the record
        self.wall: dict[str, Any] = {}
        self.extra_feed: list[dict] = []
        self.push_count: dict[str, int] = {}
        self.cursor: int | None = 0 if replay else None
        self.room_seen = 0.0

    # ------------------------------------------------------------------ #

    def server_info(self) -> dict:
        ai = self.cohost.info() if self.cohost else {"enabled": False}
        ai["reason"] = self.cohost_reason
        ai["lines_checked"] = self.checked_lines
        ai["lines_flagged"] = self.flagged_lines
        return {"version": __version__, "mode": "replay" if self.replay else "live", "ai": ai,
                "out_dir": str(self.session.out_dir), "pack_path": self.session.pack_path,
                "room_open": time.time() - self.room_seen < 4, "cursor": self.cursor}

    def boot(self) -> dict:
        """Everything the host remote needs on load. The pack is the host's own view, spoilers included."""
        state = self.session.snapshot()
        state.update({"pack": self.session.pack, "server": self.server_info(), "token": self.token})
        return state

    def _state(self) -> Response:
        state = self.session.snapshot()
        state["server"] = self.server_info()
        return _json(state)

    def _feed(self, who: str, text: str, strong: bool = False) -> None:
        with self._lock:
            self.extra_feed.append({"at": now_iso(), "who": who, "text": text, "strong": strong})
            del self.extra_feed[:-40]

    def room_state(self) -> dict:
        """The spoiler-free view for the wall."""
        snap = self.session.snapshot()
        wall = dict(self.wall)
        if wall.get("writing") and time.time() - wall.get("since", 0) > WRITING_TIMEOUT:
            wall["writing"] = False
        total = len(snap["log"].get("entries", []))
        at_end = self.cursor is None or self.cursor >= total
        report = snap.get("report") if at_end else None
        state = room.room_state(self.session.pack, snap["log"], wall=wall, extra_feed=None if self.replay else self.extra_feed,
                                report=report, cursor=self.cursor, force_ended=bool(self.replay and report))
        state["mode"] = "replay" if self.replay else "live"
        return state

    # ------------------------------------------------------------------ #

    def handle(self, method: str, path: str, body: bytes = b"", headers: dict[str, str] | None = None) -> Response:
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        path = path.split("?", 1)[0]
        if method == "GET" and path in ("/", "/index.html"):
            page = render_console(self.boot(), served=True)
            return Response(content_type="text/html; charset=utf-8", body=page.encode("utf-8"), headers={"Cache-Control": "no-store"})
        if method == "GET" and path == "/room":
            return Response(content_type="text/html; charset=utf-8", body=render_room().encode("utf-8"), headers={"Cache-Control": "no-store"})
        if method == "GET" and path == "/room/state":
            self.room_seen = time.time()
            return _json(self.room_state())
        if not path.startswith("/api/"):
            return _error("not found", 404)
        if headers.get("x-ttx-token") != self.token:
            return _error("missing or wrong session token; reload the console", 403)
        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except ValueError:
            return _error("the request body is not valid JSON")
        if not isinstance(data, dict):
            return _error("the request body must be a JSON object")
        try:
            return self._route(method, path, data)
        except LogError as exc:
            return _error(str(exc), 409)
        except (FileNotFoundError, ValueError) as exc:
            return _error(str(exc), 400)

    def _route(self, method: str, path: str, data: dict) -> Response:
        s = self.session
        if method == "GET" and path == "/api/state":
            return self._state()
        if method != "POST":
            return _error("not found", 404)
        if path == "/api/present":
            inject_id = str(data.get("inject_id") or "")
            s.present(inject_id)
            # the wall shows the pack's script at once, or waits for the co-host's checked line
            self.wall = {"inject_id": inject_id, "writing": bool(self.cohost), "since": time.time(), "line": None, "stake": None}
            return self._state()
        if path == "/api/skip":
            s.skip(str(data.get("inject_id") or ""))
            return self._state()
        if path == "/api/note":
            s.note(str(data.get("text") or ""))
            return self._state()
        if path == "/api/decision":
            s.decide(str(data.get("inject_id") or ""), str(data.get("decision") or ""), str(data.get("by") or ""),
                     notified=data.get("notified"), actions=data.get("actions"), plan_step=data.get("plan_step"),
                     documented=data.get("documented"), scenario_minutes=data.get("scenario_minutes"),
                     note=data.get("note"), unplanned=bool(data.get("unplanned")))
            return self._state()
        if path == "/api/clocks":
            owners = {k: v for k, v in (data.get("owners") or {}).items() if v}
            hours = {k: v for k, v in (data.get("planned_hours") or {}).items() if v not in (None, "")}
            s.clocks(owners=owners, planned_hours=hours)
            return self._state()
        if path == "/api/end":
            s.end()
            if not self.replay:
                self._feed("ENGINE", "score ready")
            return self._state()
        if path == "/api/open":
            return self._open(str(data.get("what") or ""))
        if path == "/api/replay/cursor":
            if not self.replay:
                return _error("this is not a replay", 409)
            total = len(s.log().get("entries", []))
            self.cursor = max(0, min(total, int(data.get("n") or 0)))
            return _json({"cursor": self.cursor})
        if path == "/api/wall/push":
            return self._push(data)
        if path == "/api/cohost/suggest":
            return self._suggest(data)
        if path == "/api/cohost/voice":
            return self._voice(data)
        return _error("not found", 404)

    # ------------------------------------------------------------------ #

    def _open(self, what: str) -> Response:
        report = self.session.snapshot().get("report")
        if not report:
            return _error("there are no reports yet; end the exercise first", 409)
        if what == "folder":
            target = Path(report["out"])
        elif what in OPENABLE:
            target = Path(report["files"][what])
        else:
            return _error(f"cannot open '{what}'")
        if not target.exists():
            return _error(f"{target.name} is missing", 404)
        from ..demo import open_folder

        opened = (self.opener or open_folder)(target)
        return _json({"opened": bool(opened), "path": str(target)})

    def _require_cohost(self) -> None:
        if self.cohost is None:
            raise LogError(self.cohost_reason or "the AI co-host is off")
        if self.session.read_only:
            raise LogError("the AI co-host is off during a replay")

    def _suggest(self, data: dict) -> Response:
        self._require_cohost()
        inject = self.session.inject(str(data.get("inject_id") or ""))
        text = str(data.get("text") or "").strip()
        if not text:
            return _error("type the room's decision first")
        try:
            suggestion = self.cohost.suggest(self.session.pack, inject, text)
        except CohostError as exc:
            return _error(str(exc), 502)
        index = self.session.inject_index(inject["id"])
        findings = conduct.check_text(suggestion.get("decision") or "", self.session.pack, index, extra=text)
        return _json({"suggestion": suggestion, "findings": findings, "ai": self.server_info()["ai"]})

    def _earlier(self, upto_index: int) -> list[dict]:
        from ..decision_log import latest_decisions

        latest = latest_decisions(self.session.log())
        roles = {r["id"]: r.get("name") for r in self.session.pack.get("roles", [])}
        out = []
        for inj in self.session.pack.get("injects", [])[:upto_index]:
            e = latest.get(inj["id"])
            if e:
                out.append({"title": inj.get("title"), "decision": e.get("decision"),
                            "decided_by": roles.get(e.get("decided_by_role"), e.get("decided_by_role"))})
        return out

    def _checked(self, findings: list[dict]) -> None:
        with self._lock:
            self.checked_lines += 1
            if findings:
                self.flagged_lines += 1

    def _voice(self, data: dict) -> Response:
        self._require_cohost()
        inject = self.session.inject(str(data.get("inject_id") or ""))
        mode = "present" if data.get("mode") == "present" else "react"
        text = str(data.get("text") or "")
        to_wall = bool(data.get("wall")) and mode == "present"
        index = self.session.inject_index(inject["id"])
        earlier = self._earlier(index)

        def on_wall(line: str | None) -> None:
            # a line reaches the wall only after the fact check has passed; otherwise the wall shows the script
            if to_wall and self.wall.get("inject_id") == inject["id"]:
                self.wall.update({"writing": False, "line": line, "source": "ai" if line else "script"})

        def events() -> Iterator[bytes]:
            parts: list[str] = []
            try:
                for chunk in self.cohost.voice(self.session.pack, inject, mode, room_text=text, earlier=earlier):
                    parts.append(chunk)
                    yield _sse("delta", {"text": chunk})
            except CohostError as exc:
                on_wall(None)
                if to_wall:
                    self._feed("GM", "co-host unavailable, showing the script")
                yield _sse("error", {"error": str(exc)})
                return
            line = "".join(parts)
            # The room's own words are allowed back: a number the room said is not a number the co-host invented.
            findings = conduct.check_text(line, self.session.pack, index, extra=text, corpus=None if text else self._corpus)
            self._checked(findings)
            if to_wall:
                on_wall(None if findings else line.strip())
                self._feed("GM", "line written from the approved exercise")
                self._feed("ENGINE", "line held back by the fact check, showing the script" if findings else "fact check passed")
            yield _sse("done", {"findings": findings, "summary": conduct.summarize(findings), "on_wall": to_wall and not findings,
                                "ai": self.server_info()["ai"]})

        return Response(content_type="text/event-stream; charset=utf-8", stream=events(),
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    def _push(self, data: dict) -> Response:
        """Put one line on the wall to press a quiet room: a stakeholder in character, or a follow-up from the script."""
        if self.session.read_only:
            raise LogError("this is a replay of a recorded session; it cannot be changed")
        inject = self.session.inject(str(data.get("inject_id") or ""))
        if self.wall.get("inject_id") != inject["id"]:
            raise LogError("present this inject before pushing the room")
        index = self.session.inject_index(inject["id"])
        count = self.push_count.get(inject["id"], 0)
        self.push_count[inject["id"]] = count + 1
        stake, note = None, ""
        if self.cohost:
            try:
                text = "".join(self.cohost.voice(self.session.pack, inject, "push", earlier=self._earlier(index)))
                findings = conduct.check_text(text, self.session.pack, index, corpus=self._corpus)
                self._checked(findings)
                parsed = parse_stake(text, self.session.pack)
                if parsed and not findings:
                    stake = {**parsed, "source": "ai"}
                else:
                    note = "The co-host's line did not pass the check, so the wall shows a follow-up from the script."
                    self._feed("ENGINE", "line held back by the fact check, using the script")
            except CohostError as exc:
                note = str(exc)
        if stake is None:
            questions = inject.get("probing_questions") or []
            if not questions:
                raise LogError("this inject has no follow-up question in the exercise pack")
            stake = {"role": "Facilitator", "text": questions[count % len(questions)], "source": "script"}
            self._feed("GM", "room is quiet, asking a follow-up from the script")
        else:
            self._feed("GM", f"room is quiet, speaking as the {stake['role']}")
            self._feed("ENGINE", "fact check passed")
        self.wall["stake"] = stake
        return _json({"stake": stake, "note": note, "ai": self.server_info()["ai"]})


# --------------------------------------------------------------------------- #
# HTTP layer
# --------------------------------------------------------------------------- #

def make_handler(app: App, allowed_hosts: set[str]):
    class Handler(BaseHTTPRequestHandler):
        server_version = f"TabletopGM/{__version__}"

        def log_message(self, fmt, *args):  # quiet: the console is the interface
            return

        def _send(self, response: Response) -> None:
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for key, value in response.headers.items():
                self.send_header(key, value)
            if response.stream is None:
                self.send_header("Content-Length", str(len(response.body)))
                self.end_headers()
                self.wfile.write(response.body)
                return
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                for chunk in response.stream:
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            self.close_connection = True

        def _dispatch(self, method: str) -> None:
            host = (self.headers.get("Host") or "").lower()
            if host not in allowed_hosts:
                self._send(_error("this console only answers on localhost", 403))
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length > 1_000_000:
                self._send(_error("request too large", 413))
                return
            body = self.rfile.read(length) if length else b""
            try:
                response = app.handle(method, self.path, body, dict(self.headers.items()))
            except Exception as exc:  # last resort: never take the console down mid-exercise
                response = _error(f"internal error: {exc.__class__.__name__}: {exc}", 500)
            try:
                self._send(response)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def do_GET(self):  # noqa: N802
            self._dispatch("GET")

        def do_POST(self):  # noqa: N802
            self._dispatch("POST")

    return Handler


def serve(app: App, port: int = 8765, open_browser: bool = True, ready=None) -> None:
    """Serve the console on 127.0.0.1 until interrupted."""
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app, hosts))
    except OSError as exc:
        raise ValueError(f"could not listen on 127.0.0.1:{port} ({exc}); choose another --port") from exc
    httpd.daemon_threads = True
    url = f"http://127.0.0.1:{port}/"
    print(f"Tabletop GM host console (your laptop, private): {url}")
    print(f"Room screen (wall, projector, or shared window): {url}room")
    print(f"exercise: {app.session.pack.get('title')}")
    print(f"record:   {app.session.out_dir}")
    print(f"co-host:  {app.cohost_reason}")
    print("Press Ctrl+C to stop. The decision log is saved after every entry.")
    sys.stdout.flush()
    if ready is not None:
        ready(httpd)
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        httpd.server_close()
