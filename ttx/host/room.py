"""What the room is allowed to see. No model, no network.

``ttx host`` serves two pages. The host remote is private: it holds the plan
quotes, the expected answers, and the deadlines. The room screen goes on the
wall, and it is built only from this module's output, which never contains:

  an inject the facilitator has not presented yet
  a system on the attack path the story has not reached yet
  an expected action, a plan quote, a good answer, or where teams fail
  the notification clock table: its deadlines, owners, and answers
  a score, until the exercise has ended

The only inject text it carries is what the pack gives the host to say out loud:
the title, the line to read, and the decision. Everything here is derived from
the approved pack and the decision log. The only extra input is ``wall``: the
line currently on the wall, which the server sets after the fact check has
passed.
"""

from __future__ import annotations

import re
from typing import Any

from ..common import now_iso
from .session import END_NOTE

PATH_STEPS = (("entry", "Entry point"), ("pivot", "Pivot"), ("target", "Target"))
FEED_LINES = 7


def _visible(log: dict, cursor: int | None) -> list[dict]:
    entries = log.get("entries", [])
    vis = entries if cursor is None else entries[:max(0, cursor)]
    last_n = vis[-1]["n"] if vis else 0
    return [e for e in vis if not (e.get("superseded_by") and e["superseded_by"] <= last_n)]


def _role_name(pack: dict, role_id: str | None) -> str:
    for r in pack.get("roles", []):
        if r["id"] == role_id:
            return r.get("name") or role_id
    return "someone outside the plan" if role_id == "other" else (role_id or "")


def _number(pack: dict, inject_id: str) -> int:
    return [j["id"] for j in pack.get("injects", [])].index(inject_id) + 1


def script_line(inject: dict) -> str:
    """The pack's own line for the host to read aloud."""
    return (inject.get("host_lines") or [inject.get("what_happens") or ""])[0]


def feed_from_log(pack: dict, log: dict, cursor: int | None = None) -> list[dict]:
    """The engine's side of the activity feed: one or two lines per log entry, nothing the room has not seen."""
    injects = {j["id"]: j for j in pack.get("injects", [])}
    approval = str(log.get("approval_hash") or "")[:8]
    out = [{"at": log.get("started_at"), "who": "ENGINE", "text": f"session started, approval {approval} verified"}]
    for e in _visible(log, cursor):
        kind, at = e.get("type"), e.get("at")
        inj = injects.get(e.get("inject_id") or "")
        n = f"{_number(pack, inj['id']):02d}" if inj else ""
        if kind == "mark" and e.get("event") == "presented":
            out.append({"at": at, "who": "GM", "text": f"presenting inject {n}"})
            out.append({"at": at, "who": "ENGINE", "text": "discussion clock started"})
            if inj["id"] == pack.get("clock_start_inject") or ((inj.get("flags") or {}).get("starts_clock") or []):
                out.append({"at": at, "who": "ENGINE", "text": "notification clocks started"})
        elif kind == "mark":
            out.append({"at": at, "who": "GM", "text": f"inject {n} skipped by the host"})
        elif kind == "decision":
            what = "unplanned action logged" if e.get("unplanned") else "decision logged"
            out.append({"at": at, "who": "ENGINE", "text": f"{what}, inject {n}, {_role_name(pack, e.get('decided_by_role'))}"})
        elif kind == "clocks":
            out.append({"at": at, "who": "ENGINE", "text": "notification owners recorded"})
        elif kind == "note" and e.get("text") == END_NOTE:
            out.append({"at": at, "who": "ENGINE", "text": "exercise ended, scoring the record"})
    return out


def _told(inject: dict) -> str:
    """The words of an inject that go on the wall: its title, the line read aloud, and the decision."""
    return " ".join([str(inject.get("title") or ""), script_line(inject), str(inject.get("decision_forced") or "")]).lower()


def path_view(pack: dict, presented: list[dict], current: dict | None = None) -> list[dict]:
    """The attack path as far as the story has gone. Systems not reached yet stay unnamed.

    The attacker marker sits on the furthest system reached so far.
    """
    seed = pack.get("seed") or {}
    steps = [(label, seed.get(key) or {}) for key, label in PATH_STEPS if (seed.get(key) or {}).get("asset")]
    reached: dict[int, str] = {}
    for inj in presented:
        ref = (inj.get("source") or {}).get("ref")
        told = _told(inj)
        for i, (_, s) in enumerate(steps):
            # a step is reached when an inject cites its finding, or names its system in words already on the wall
            if s.get("finding_id") == ref or re.search(r"(?<![\w-])" + re.escape(str(s["asset"]).lower()) + r"(?![\w-])", told):
                reached.setdefault(i, inj.get("time_marker") or "")
    furthest = max(reached, default=-1)
    nodes = []
    for i, (label, s) in enumerate(steps):
        if i > furthest:
            nodes.append({"label": label, "asset": None, "detail": None, "state": "unknown", "since": None})
            continue
        detail = "internet-facing" if s.get("internet_facing") else (", ".join(s.get("data") or []) or None)
        nodes.append({"label": label, "asset": s.get("asset"), "detail": detail,
                      "state": "active" if i == furthest else "passed", "since": reached.get(i)})
    return nodes


def room_state(pack: dict, log: dict, wall: dict | None = None, extra_feed: list[dict] | None = None,
               report: dict | None = None, cursor: int | None = None, now: str | None = None,
               force_ended: bool = False) -> dict:
    """Everything the room screen renders. See the module docstring for what can never be in it."""
    wall = wall or {}
    vis = _visible(log, cursor)
    injects = {j["id"]: j for j in pack.get("injects", [])}
    presented = [injects[e["inject_id"]] for e in vis if e.get("type") == "mark" and e.get("event") == "presented" and e.get("inject_id") in injects]
    presented_at = {e["inject_id"]: e["at"] for e in vis if e.get("type") == "mark" and e.get("event") == "presented"}
    # a recording may stop without an end note; a replay that has been scored counts as ended
    ended = force_ended or any(e.get("type") == "note" and e.get("text") == END_NOTE for e in vis)
    current = presented[-1] if presented else None

    state: dict[str, Any] = {
        "organization": (pack.get("organization") or {}).get("name"),
        "title": pack.get("title"),
        "total": len(pack.get("injects", [])),
        "ground_rules": list(pack.get("ground_rules") or [])[:3],
        "started_at": log.get("started_at"),
        "now": now or now_iso(),
        # a replay shows the recorded discussion time, not time since the recording
        "as_of": (vis[-1].get("at") if vis else None) if cursor is not None else None,
        "ended": ended,
        "path": path_view(pack, presented, current),
        "inject": None, "line": None, "stake": None, "logged": None, "score": None,
    }
    if current:
        cid = current["id"]
        state["inject"] = {
            "id": cid, "n": _number(pack, cid), "phase": current.get("phase"), "time_marker": current.get("time_marker"),
            "title": current.get("title"), "decision": current.get("decision_forced"),
            "owner": _role_name(pack, current.get("decision_owner_role")), "presented_at": presented_at.get(cid),
        }
        mine = wall if wall.get("inject_id") == cid else {}
        if mine.get("writing"):
            state["line"] = {"text": "", "source": "ai", "writing": True, "checked": False}
        elif mine.get("line"):
            state["line"] = {"text": mine["line"], "source": mine.get("source") or "script", "writing": False,
                             "checked": mine.get("source") == "ai"}
        else:
            state["line"] = {"text": script_line(current), "source": "script", "writing": False, "checked": False}
        if mine.get("stake"):
            state["stake"] = dict(mine["stake"])
        decisions = [e for e in vis if e.get("type") == "decision" and not e.get("unplanned") and e.get("inject_id") == cid]
        if decisions:
            d = decisions[-1]
            state["logged"] = {"at": d.get("at"), "by": _role_name(pack, d.get("decided_by_role")), "decision": d.get("decision")}
    feed = feed_from_log(pack, log, cursor) + list(extra_feed or [])
    state["feed"] = sorted(feed, key=lambda f: f.get("at") or "")[-FEED_LINES:]
    if ended and report:
        summary = report.get("summary") or {}
        labels = report.get("dimension_labels") or {}
        averages = summary.get("dimension_averages") or {}
        state["score"] = {
            "rating": report.get("rating"), "percent": report.get("percent"), "headline": report.get("headline"),
            "decisions_scored": summary.get("injects_scored"), "decisions_total": summary.get("injects_total"),
            "deadlines_met": summary.get("clocks_met"), "deadlines_total": len(report.get("clocks") or []),
            "dimensions": [{"label": labels[k], "average": averages.get(k)} for k in labels],
        }
    return state
