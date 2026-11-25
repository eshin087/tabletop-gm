"""One live exercise for the host console: the approved pack plus its decision log.

The session keeps no state of its own. Everything the console shows is derived
from the pack and the append-only log, so a restarted server resumes exactly
where the room left off, and a recorded log can be replayed with no model.
"""

from __future__ import annotations

import shutil
import threading
from pathlib import Path
from typing import Any

from .. import decision_log as dl
from ..common import read_json

END_NOTE = "Exercise ended"


class HostSession:
    """Thread-safe wrapper over ``ttx.decision_log`` for one pack and one output folder."""

    def __init__(self, pack_path: str | Path, out_dir: str | Path, facilitator: str, resume: bool = False,
                 now: str | None = None):
        self.pack_path = str(pack_path)
        self.out_dir = Path(out_dir)
        self.read_only = False
        self._lock = threading.RLock()
        self._report: dict | None = None
        log = dl.start(self.pack_path, self.out_dir, facilitator, resume=resume, now=now)
        self.pack = dl.load_pack_for(log, self.pack_path)

    @classmethod
    def replay(cls, log_file: str | Path, out_dir: str | Path, pack_path: str | Path | None = None) -> "HostSession":
        """Open a recorded log read-only. The log is copied into out_dir so reports never touch the original."""
        src = Path(log_file)
        if not src.exists():
            raise FileNotFoundError(f"decision log not found: {src}")
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        dest = dl.log_path(out)
        if src.resolve() != dest.resolve():
            shutil.copyfile(src, dest)
        self = cls.__new__(cls)
        self.out_dir = out
        self.read_only = True
        self._lock = threading.RLock()
        self._report = None
        log = read_json(dest)
        self.pack_path = str(pack_path or log["pack_path"])
        self.pack = dl.load_pack_for(log, self.pack_path)
        return self

    # ------------------------------------------------------------------ #
    # Reading
    # ------------------------------------------------------------------ #

    def log(self) -> dict:
        with self._lock:
            return dl.load_log(self.out_dir)

    def ended(self, log: dict | None = None) -> bool:
        log = log or self.log()
        return any(e.get("type") == "note" and e.get("text") == END_NOTE for e in log.get("entries", []))

    def snapshot(self) -> dict:
        """What the console needs after any change: the log, and the score once the exercise has ended."""
        with self._lock:
            log = dl.load_log(self.out_dir)
            ended = self.ended(log)
            if ended and self._report is None:
                # a restarted server shows the score of a finished exercise again; scoring is deterministic
                self.report()
            return {"log": log, "ended": ended, "report": self._report, "read_only": self.read_only}

    def inject(self, inject_id: str) -> dict:
        for inj in self.pack.get("injects", []):
            if inj["id"] == inject_id:
                return inj
        raise dl.LogError(f"unknown inject id '{inject_id}'")

    def inject_index(self, inject_id: str) -> int:
        return [j["id"] for j in self.pack.get("injects", [])].index(self.inject(inject_id)["id"])

    # ------------------------------------------------------------------ #
    # Mutations: each one is a single ttx.decision_log call
    # ------------------------------------------------------------------ #

    def _mutate(self, fn, *args, **kwargs) -> dict:
        if self.read_only:
            raise dl.LogError("this is a replay of a recorded session; it cannot be changed")
        with self._lock:
            log = dl.load_log(self.out_dir)
            if self.ended(log):
                raise dl.LogError("the exercise has ended; corrections go through ttx log edit")
            fn(log, *args, **kwargs)
            dl.save_log(self.out_dir, log)
            return self.snapshot()

    def present(self, inject_id: str, now: str | None = None) -> dict:
        return self._mutate(dl.add_mark, self.pack, inject_id, "presented", now=now)

    def skip(self, inject_id: str, now: str | None = None) -> dict:
        return self._mutate(dl.add_mark, self.pack, inject_id, "skipped", now=now)

    def note(self, text: str, now: str | None = None) -> dict:
        return self._mutate(dl.add_note, text, now=now)

    def decide(self, inject_id: str, decision: str, by: str, notified: Any = None, actions: Any = None,
               plan_step: str | None = None, documented: str | None = None, scenario_minutes: Any = None,
               note: str | None = None, unplanned: bool = False, now: str | None = None) -> dict:
        return self._mutate(dl.add_decision, self.pack, inject_id, decision, by, notified=notified, actions=actions,
                            plan_step=plan_step or None, documented=documented or None,
                            scenario_minutes=scenario_minutes, note=note or None, unplanned=unplanned, now=now)

    def clocks(self, owners: dict | None = None, planned_hours: dict | None = None, now: str | None = None) -> dict:
        return self._mutate(dl.add_clocks, self.pack, owners=owners, planned_hours=planned_hours, now=now)

    # ------------------------------------------------------------------ #
    # The end: one note, then the same report pipeline as ttx report --log
    # ------------------------------------------------------------------ #

    def end(self, now: str | None = None) -> dict:
        with self._lock:
            if not self.read_only and not self.ended():
                log = dl.load_log(self.out_dir)
                dl.add_note(log, END_NOTE, now=now)
                dl.save_log(self.out_dir, log)
            self.report()
            return self.snapshot()

    def report(self) -> dict:
        """Score the log and write the after-action report and executive summary next to it."""
        from ..report import run_report

        with self._lock:
            result = run_report(pack_path=self.pack_path, log_path=str(dl.log_path(self.out_dir)))
            score = read_json(result["files"]["score"])
            self._report = {
                "headline": result["headline"], "rating": result["rating"], "percent": result["percent"],
                "worked": result["worked"], "improve": result["improve"], "files": result["files"], "out": result["out"],
                "summary": score["summary"], "dimension_labels": score["dimension_labels"],
                "injects": [{"inject_id": r["inject_id"], "title": r.get("title"), "reached": r.get("reached"),
                             "total": r.get("total"), "max": r.get("max"), "scores": r.get("scores"), "reasons": r.get("reasons")}
                            for r in score.get("injects", [])],
                "clocks": score.get("clocks", []),
                "gaps": [{"id": g.get("id"), "label": g.get("label"), "finding": g.get("finding"), "fix": g.get("fix"),
                          "owner": g.get("owner"), "due": g.get("due")} for g in score.get("gaps", [])],
            }
            return self._report
