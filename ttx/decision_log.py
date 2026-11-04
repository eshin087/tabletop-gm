"""Live decision log: the append-only record behind ``ttx log``.

When Claude facilitates an exercise in chat, the host types what the room
decides and the engine records it here, in ``out/live/decision_log.json``.
Every mutation appends an entry; nothing is destroyed. A correction appends a
new version and marks the original ``superseded_by``. Wall-clock timestamps
come from this module, never from the model.

Entry types:

  decision   a decision at an inject (``unplanned: true`` when the plan did not
             anticipate it; unplanned entries are shown in the AAR, never scored)
  mark       an inject was presented or skipped
  note       a freeform facilitator note
  clocks     the team's clock answers (owner role, planned notification hours)

``export`` writes ``decisions.csv`` and ``decisions_clocks.csv`` in exactly the
decision tracker's column shapes (``schemas/tracker_columns.yaml``), so
``ttx score`` reads them unchanged. The JSON log stays as the audit original.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from . import __version__
from .common import as_list, now_iso, parse_iso, read_json, write_json
from .score_engine import CLOCK_COLUMNS, DECISION_COLUMNS
from .validators import check_approval

LOG_NAME = "decision_log.json"
DECISIONS_CSV = "decisions.csv"
CLOCKS_CSV = "decisions_clocks.csv"
PLAN_STEPS = ["yes", "partial", "no", "plan_unclear", "n/a"]
DOCUMENTED = ["yes", "partial", "no"]
MARK_EVENTS = ["presented", "skipped"]
OTHER_ROLE = "other"
EDITABLE = ["decision", "decided_by_role", "notified", "actions_completed", "plan_step_followed", "documented",
            "scenario_minutes", "discussion_minutes", "note"]


class LogError(ValueError):
    """A refused log operation. The CLI prints the message and exits 2."""


# --------------------------------------------------------------------------- #
# Files
# --------------------------------------------------------------------------- #

def log_path(out_dir: str | Path) -> Path:
    return Path(out_dir) / LOG_NAME


def load_log(out_dir: str | Path) -> dict:
    p = log_path(out_dir)
    if not p.exists():
        raise LogError(f"no decision log at {p}; run ttx log start first")
    return read_json(p)


def save_log(out_dir: str | Path, log: dict) -> Path:
    p = log_path(out_dir)
    write_json(p, log)
    return p


def load_pack_for(log: dict, pack_path: str | Path | None = None) -> dict:
    """Load the approved pack this log belongs to and confirm it has not changed."""
    path = pack_path or log["pack_path"]
    pack = read_json(path)
    _require_approved(pack)
    if pack["approval"]["outline_hash"] != log["approval_hash"]:
        raise LogError(f"{path} carries approval hash {pack['approval']['outline_hash'][:12]}, but this log was started "
                       f"with {log['approval_hash'][:12]}; the pack changed after the session started")
    return pack


def _require_approved(pack: dict) -> None:
    gate = check_approval(pack)
    if not gate.ok:
        raise LogError("refusing: " + "; ".join(gate.errors))


def _now(now: str | None) -> str:
    return now or now_iso()


# --------------------------------------------------------------------------- #
# Lookups
# --------------------------------------------------------------------------- #

def _injects(pack: dict) -> dict[str, dict]:
    return {j["id"]: j for j in pack.get("injects", [])}


def _role_ids(pack: dict) -> list[str]:
    return [r["id"] for r in pack.get("roles", [])]


def _party_ids(pack: dict) -> list[str]:
    return [p["id"] for p in pack.get("notify_parties", [])]


def _clock_ids(pack: dict) -> list[str]:
    return [c["id"] for c in pack.get("clocks", [])]


def _role_name(pack: dict, role_id: str | None) -> str | None:
    if not role_id:
        return None
    for r in pack.get("roles", []):
        if r["id"] == role_id:
            return r.get("name") or role_id
    return role_id


def _check_inject(pack: dict, inject_id: str) -> dict:
    injects = _injects(pack)
    if inject_id not in injects:
        raise LogError(f"unknown inject id '{inject_id}'; this pack has {', '.join(injects)}")
    return injects[inject_id]


def _check_role(pack: dict, role_id: str | None, note: str | None) -> str:
    if not role_id:
        raise LogError("a deciding role is required (--by <role_id>, or --by other with --note)")
    if role_id == OTHER_ROLE:
        if not note:
            raise LogError("--by other needs --note saying who decided")
        return role_id
    roles = _role_ids(pack)
    if role_id not in roles:
        raise LogError(f"unknown role id '{role_id}'; pack roles: {', '.join(roles)}. For someone outside the pack use --by other --note '...'")
    return role_id


def _check_parties(pack: dict, notified: Any) -> list[str]:
    ids = [str(x).strip() for x in as_list(notified) if str(x).strip()]
    known = _party_ids(pack)
    bad = [x for x in ids if x not in known]
    if bad:
        raise LogError(f"unknown notified party id(s) {bad}; pack parties: {', '.join(known)}. Put anyone else in --note")
    return ids


def _check_actions(inj: dict, actions: Any) -> list[str]:
    ids = [str(x).strip() for x in as_list(actions) if str(x).strip()]
    known = [a["id"] for a in inj.get("expected_actions", [])]
    bad = [x for x in ids if x not in known]
    if bad:
        raise LogError(f"unknown action id(s) {bad} for {inj['id']}; expected actions: {', '.join(known) or 'none'}")
    return ids


def _check_choice(value: str | None, choices: list[str], flag: str) -> str | None:
    if value is None:
        return None
    v = str(value).strip().lower()
    if v not in choices:
        raise LogError(f"{flag} must be one of {', '.join(choices)}; got '{value}'")
    return v


def _check_minutes(value: Any, flag: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        m = float(value)
    except (TypeError, ValueError):
        raise LogError(f"{flag} must be a number of minutes; got '{value}'") from None
    if m < 0:
        raise LogError(f"{flag} cannot be negative")
    return m


# --------------------------------------------------------------------------- #
# Mutations (every one appends)
# --------------------------------------------------------------------------- #

def _append(log: dict, entry: dict, at: str) -> dict:
    full = {"n": len(log["entries"]) + 1, "at": at}
    full.update(entry)
    log["entries"].append(full)
    if at > (log.get("last_activity_at") or ""):
        log["last_activity_at"] = at
    return full


def start(pack_path: str | Path, out_dir: str | Path, by: str, resume: bool = False, now: str | None = None) -> dict:
    """Create the log for an approved pack. Refuses an unapproved or tampered pack and an existing log unless resuming."""
    pack = read_json(pack_path)
    _require_approved(pack)
    at = _now(now)
    p = log_path(out_dir)
    if p.exists():
        if not resume:
            raise LogError(f"{p} already exists; pass --resume to continue that session, or choose another --out")
        log = read_json(p)
        if log.get("approval_hash") != pack["approval"]["outline_hash"]:
            raise LogError("the existing log belongs to a different approval of this pack; start in a fresh --out directory")
        log.setdefault("resumed_at", []).append(at)
        _append(log, {"type": "note", "text": f"Session resumed by {by}"}, at)
        save_log(out_dir, log)
        return log
    org = pack.get("organization") or {}
    log = {
        "schema_version": 1,
        "generator": f"Tabletop GM ttx {__version__}",
        "pack_path": str(pack_path),
        "pack_title": pack.get("title"),
        "organization": org.get("name"),
        "approval_hash": pack["approval"]["outline_hash"],
        "approved_by": pack["approval"].get("approved_by"),
        "facilitator": by,
        "started_at": at,
        "resumed_at": [],
        "last_activity_at": at,
        "entries": [],
    }
    save_log(out_dir, log)
    return log


def add_decision(log: dict, pack: dict, inject_id: str, decision: str, by: str, notified: Any = None, actions: Any = None,
                 plan_step: str | None = None, documented: str | None = None, scenario_minutes: Any = None,
                 note: str | None = None, unplanned: bool = False, now: str | None = None) -> dict:
    """Append one decision. discussion_minutes is the wall-clock delta since the previous entry or the session start."""
    inj = _check_inject(pack, inject_id)
    if not decision or not str(decision).strip():
        raise LogError("--decision cannot be empty")
    role = _check_role(pack, by, note)
    at = _now(now)
    prev = log.get("last_activity_at") or log["started_at"]
    delta = (parse_iso(at) - parse_iso(prev)).total_seconds() / 60.0
    entry = {
        "type": "decision",
        "inject_id": inj["id"],
        "unplanned": bool(unplanned),
        "decision": str(decision).strip(),
        "decided_by_role": role,
        "notified": _check_parties(pack, notified),
        "actions_completed": _check_actions(inj, actions),
        "plan_step_followed": _check_choice(plan_step, PLAN_STEPS, "--plan-step"),
        "documented": _check_choice(documented, DOCUMENTED, "--documented"),
        "scenario_minutes": _check_minutes(scenario_minutes, "--scenario-minutes"),
        "discussion_minutes": round(max(delta, 0.0), 1),
        "note": note,
    }
    return _append(log, entry, at)


def add_note(log: dict, text: str, now: str | None = None) -> dict:
    if not text or not str(text).strip():
        raise LogError("--text cannot be empty")
    return _append(log, {"type": "note", "text": str(text).strip()}, _now(now))


def add_mark(log: dict, pack: dict, inject_id: str, event: str, now: str | None = None) -> dict:
    inj = _check_inject(pack, inject_id)
    ev = _check_choice(event, MARK_EVENTS, "--event")
    return _append(log, {"type": "mark", "inject_id": inj["id"], "event": ev}, _now(now))


def add_clocks(log: dict, pack: dict, owners: dict[str, str] | None = None, planned_hours: dict[str, Any] | None = None,
               now: str | None = None) -> dict:
    """Record the team's clock answers. Later entries override earlier ones clock by clock."""
    owners = dict(owners or {})
    planned_hours = dict(planned_hours or {})
    if not owners and not planned_hours:
        raise LogError("give at least one --owner clock_id=role_id or --planned-hours clock_id=N")
    clocks = _clock_ids(pack)
    roles = _role_ids(pack)
    for cid in list(owners) + list(planned_hours):
        if cid not in clocks:
            raise LogError(f"unknown clock id '{cid}'; pack clocks: {', '.join(clocks)}")
    for cid, role in owners.items():
        if role not in roles:
            raise LogError(f"unknown role id '{role}' for clock {cid}; pack roles: {', '.join(roles)}")
    hours: dict[str, float] = {}
    for cid, h in planned_hours.items():
        try:
            hours[cid] = float(h)
        except (TypeError, ValueError):
            raise LogError(f"planned hours for {cid} must be a number; got '{h}'") from None
        if hours[cid] < 0:
            raise LogError(f"planned hours for {cid} cannot be negative")
    return _append(log, {"type": "clocks", "owners": owners, "planned_notify_hours": hours}, _now(now))


def edit_decision(log: dict, pack: dict, entry_n: int, by: str, changes: dict[str, Any], now: str | None = None) -> dict:
    """Append a corrected version of decision entry N. The original stays, marked superseded_by."""
    original = next((e for e in log["entries"] if e["n"] == entry_n), None)
    if original is None:
        raise LogError(f"no entry {entry_n}; the log has {len(log['entries'])} entries")
    if original.get("type") != "decision":
        raise LogError(f"entry {entry_n} is a {original.get('type')} entry; only decision entries can be edited (append a note instead)")
    if original.get("superseded_by"):
        raise LogError(f"entry {entry_n} was already corrected by entry {original['superseded_by']}; edit that one")
    if not by or not str(by).strip():
        raise LogError("--by is required: who asked for the correction")
    changes = {k: v for k, v in changes.items() if v is not None}
    unknown = [k for k in changes if k not in EDITABLE]
    if unknown:
        raise LogError(f"cannot edit {unknown}; editable fields: {', '.join(EDITABLE)}")
    if not changes:
        raise LogError("nothing to change; give at least one field")
    inj = _check_inject(pack, original["inject_id"])
    new = {k: v for k, v in original.items() if k not in {"n", "at", "superseded_by"}}
    for key, value in changes.items():
        if key == "decided_by_role":
            new[key] = _check_role(pack, value, changes.get("note", original.get("note")))
        elif key == "notified":
            new[key] = _check_parties(pack, value)
        elif key == "actions_completed":
            new[key] = _check_actions(inj, value)
        elif key == "plan_step_followed":
            new[key] = _check_choice(value, PLAN_STEPS, "--plan-step")
        elif key == "documented":
            new[key] = _check_choice(value, DOCUMENTED, "--documented")
        elif key in {"scenario_minutes", "discussion_minutes"}:
            new[key] = _check_minutes(value, f"--{key.replace('_', '-')}")
        elif key == "decision":
            if not str(value).strip():
                raise LogError("--decision cannot be empty")
            new[key] = str(value).strip()
        else:
            new[key] = value
    at = _now(now)
    new["supersedes"] = entry_n
    new["edited_by"] = str(by).strip()
    new["edited_at"] = at
    # the corrected version keeps the original wall-clock time so the timeline stays truthful
    saved = _append(log, new, original["at"])
    if at > (log.get("last_activity_at") or ""):
        log["last_activity_at"] = at
    original["superseded_by"] = saved["n"]
    return saved


# --------------------------------------------------------------------------- #
# Reading the log
# --------------------------------------------------------------------------- #

def current_entries(log: dict) -> list[dict]:
    """Entries in order, without versions that were later corrected."""
    return [e for e in log.get("entries", []) if not e.get("superseded_by")]


def latest_decisions(log: dict) -> dict[str, dict]:
    """The scored decision per inject: the last current planned entry for it."""
    out: dict[str, dict] = {}
    for e in current_entries(log):
        if e.get("type") == "decision" and not e.get("unplanned"):
            out[e["inject_id"]] = e
    return out


def clock_answers(log: dict) -> dict[str, dict]:
    """{clock_id: {owner_role, planned_notify_hours}} with later answers overriding earlier ones."""
    out: dict[str, dict] = {}
    for e in current_entries(log):
        if e.get("type") != "clocks":
            continue
        for cid, role in (e.get("owners") or {}).items():
            out.setdefault(cid, {})["owner_role"] = role
        for cid, h in (e.get("planned_notify_hours") or {}).items():
            out.setdefault(cid, {})["planned_notify_hours"] = h
    return out


def skipped_injects(log: dict) -> list[str]:
    return [e["inject_id"] for e in log.get("entries", []) if e.get("type") == "mark" and e.get("event") == "skipped"]


def session_end(log: dict) -> str | None:
    return log.get("last_activity_at") or (log["entries"][-1]["at"] if log.get("entries") else None)


def _fmt_time(value: str | None) -> str:
    dt = parse_iso(value)
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z").strip()


def _fmt_num(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{f:g}"


def show(log: dict, pack: dict | None = None) -> str:
    """The log as a readable table."""
    lines = [f"Decision log: {log.get('pack_title')}  ({log.get('organization')})",
             f"facilitator {log.get('facilitator')}; started {_fmt_time(log.get('started_at'))}; last activity {_fmt_time(session_end(log))}; "
             f"approval hash {str(log.get('approval_hash'))[:12]}", ""]
    header = f"{'#':>3}  {'time':<8} {'type':<8} {'inject':<7} {'who':<22} {'min':>5}  entry"
    lines.append(header)
    lines.append("-" * len(header))
    for e in log.get("entries", []):
        t = parse_iso(e["at"]).strftime("%H:%M:%S")
        kind = e.get("type", "")
        inject = e.get("inject_id") or ""
        who = ""
        mins = ""
        text = ""
        if kind == "decision":
            who = (_role_name(pack, e.get("decided_by_role")) if pack else e.get("decided_by_role")) or ""
            mins = _fmt_num(e.get("discussion_minutes"))
            text = e.get("decision") or ""
            tags = []
            if e.get("unplanned"):
                tags.append("unplanned")
            if e.get("supersedes"):
                tags.append(f"corrects #{e['supersedes']}")
            if e.get("superseded_by"):
                tags.append(f"superseded by #{e['superseded_by']}")
            if tags:
                text = f"[{', '.join(tags)}] {text}"
        elif kind == "mark":
            text = f"inject {e.get('event')}"
        elif kind == "note":
            text = e.get("text") or ""
        elif kind == "clocks":
            parts = [f"{cid} owner {r}" for cid, r in (e.get("owners") or {}).items()]
            parts += [f"{cid} planned {_fmt_num(h)} h" for cid, h in (e.get("planned_notify_hours") or {}).items()]
            text = "; ".join(parts)
        lines.append(f"{e['n']:>3}  {t:<8} {kind:<8} {inject:<7} {who[:22]:<22} {mins:>5}  {text}")
    if not log.get("entries"):
        lines.append("(no entries yet)")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Export in the tracker's shapes
# --------------------------------------------------------------------------- #

def decision_rows(log: dict, pack: dict) -> list[dict]:
    """One row per pack inject, in pack order, in DECISION_COLUMNS shape. Unreached and skipped injects keep blank inputs."""
    latest = latest_decisions(log)
    skipped = set(skipped_injects(log))
    rows = []
    for inj in pack.get("injects", []):
        e = latest.get(inj["id"])
        row = {
            "inject_id": inj["id"],
            "slide": inj.get("slide_number"),
            "time_marker": inj.get("time_marker"),
            "phase": inj.get("phase"),
            "title": inj.get("title"),
            "expected_owner": inj.get("decision_owner_role"),
            "decision": None, "decided_by_role": None, "discussion_minutes": None, "scenario_minutes": None,
            "notified": None, "actions_completed": None, "plan_step_followed": None, "documented": None, "notes": None,
        }
        if e is not None:
            row.update({
                "decision": e.get("decision"),
                "decided_by_role": e.get("decided_by_role"),
                "discussion_minutes": e.get("discussion_minutes"),
                "scenario_minutes": e.get("scenario_minutes"),
                "notified": ",".join(e.get("notified") or []),
                "actions_completed": ",".join(e.get("actions_completed") or []),
                "plan_step_followed": e.get("plan_step_followed"),
                "documented": e.get("documented"),
                "notes": e.get("note"),
            })
        elif inj["id"] in skipped:
            row["notes"] = "skipped by the host"
        rows.append(row)
    return rows


def clock_rows(log: dict, pack: dict) -> list[dict]:
    """One row per pack clock in CLOCK_COLUMNS shape, prefilled like the tracker's Clocks sheet."""
    answers = clock_answers(log)
    internal = {i.get("applies_to_clock"): i.get("internal_deadline_hours")
                for i in (pack.get("org_plan") or {}).get("items", []) if i.get("applies_to_clock")}
    rows = []
    for c in pack.get("clocks", []):
        a = answers.get(c["id"], {})
        rows.append({
            "clock_id": c["id"],
            "name": c.get("name"),
            "deadline_hours": c.get("deadline_hours"),
            "deadline_business_days": c.get("deadline_business_days"),
            "tier": c.get("tier"),
            "owner_role": a.get("owner_role"),
            "planned_notify_hours": a.get("planned_notify_hours"),
            "internal_deadline_hours": internal.get(c["id"]),
            "notes": "VERIFY BEFORE EXERCISE (researched tier)" if c.get("tier") != "verified" else None,
        })
    return rows


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({c: ("" if row.get(c) is None else row.get(c)) for c in columns})


def export(log: dict, pack: dict, out_dir: str | Path) -> dict[str, str]:
    out = Path(out_dir)
    decisions = out / DECISIONS_CSV
    clocks = out / CLOCKS_CSV
    _write_csv(decisions, DECISION_COLUMNS, decision_rows(log, pack))
    _write_csv(clocks, CLOCK_COLUMNS, clock_rows(log, pack))
    return {"decisions": str(decisions), "clocks": str(clocks), "log": str(log_path(out_dir))}


# --------------------------------------------------------------------------- #
# Timeline for the AAR appendix
# --------------------------------------------------------------------------- #

def timeline(log: dict, pack: dict, score: dict | None = None) -> list[dict]:
    """Every entry, in order, as display rows: wall clock, scenario time, entry text, owner, score where scored."""
    injects = _injects(pack)
    scored = {r["inject_id"]: r for r in (score or {}).get("injects", [])}
    latest = latest_decisions(log)
    rows = []
    for e in log.get("entries", []):
        kind = e.get("type")
        inj = injects.get(e.get("inject_id") or "", {})
        row = {"n": e["n"], "wall_clock": _fmt_time(e["at"]), "scenario_time": inj.get("time_marker") or "",
               "inject_id": e.get("inject_id") or "", "type": kind, "entry": "", "owner": "", "score": ""}
        if kind == "decision":
            tags = []
            if e.get("unplanned"):
                tags.append("unplanned")
            if e.get("supersedes"):
                tags.append(f"corrects entry {e['supersedes']}, by {e.get('edited_by')}")
            if e.get("superseded_by"):
                tags.append(f"superseded by entry {e['superseded_by']}")
            text = e.get("decision") or ""
            if e.get("note"):
                text += f" Note: {e['note']}"
            row["entry"] = (f"[{'; '.join(tags)}] " if tags else "") + text
            row["owner"] = _role_name(pack, e.get("decided_by_role")) or ""
            if e.get("unplanned"):
                row["score"] = "not scored (unplanned)"
            elif e.get("superseded_by"):
                row["score"] = "superseded"
            elif latest.get(e["inject_id"]) is e:
                res = scored.get(e["inject_id"])
                if res and res.get("reached"):
                    row["score"] = f"{res.get('total', 0)}/{res.get('max', 0)}"
                elif score is not None:
                    row["score"] = "not scored"
        elif kind == "mark":
            row["entry"] = f"Inject {e.get('inject_id')} {'presented' if e.get('event') == 'presented' else 'skipped by the host'}: {inj.get('title') or ''}".rstrip(": ")
        elif kind == "note":
            row["entry"] = f"Note: {e.get('text') or ''}"
        elif kind == "clocks":
            names = {c["id"]: c.get("name") or c["id"] for c in pack.get("clocks", [])}
            parts = []
            for cid, r in (e.get("owners") or {}).items():
                parts.append(f"{names.get(cid, cid)}: owner {_role_name(pack, r)}")
            for cid, h in (e.get("planned_notify_hours") or {}).items():
                parts.append(f"{names.get(cid, cid)}: planned notification at {_fmt_num(h)} hours")
            row["entry"] = "Clock answers. " + "; ".join(parts)
        rows.append(row)
    return rows


def session_summary(log: dict, log_file: str | Path | None = None) -> str:
    end = session_end(log)
    resumed = log.get("resumed_at") or []
    text = (f"Facilitated by {log.get('facilitator')}. Session started {_fmt_time(log.get('started_at'))}"
            f" and ended {_fmt_time(end)}" + (f", resumed {len(resumed)} time(s)" if resumed else "") + ". "
            f"{len(log.get('entries', []))} entries. The audit original is {log_file or LOG_NAME}; "
            f"this appendix is rendered from it without change.")
    return text
