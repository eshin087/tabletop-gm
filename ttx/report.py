"""After the exercise, in one step: find the tracker, score it, write every report.

  ttx report                       finds out/exercise_pack.json and the filled tracker
  ttx report --tracker <file>      use a specific tracker (.xlsx or .csv decision log)

Outputs (default out/report/): score.json, after_action_report.docx,
executive_summary.pptx, executive_summary.docx. No network, no model.
"""

from __future__ import annotations

from pathlib import Path

from .common import read_json, write_json


def find_pack(explicit: str | None = None, root: Path | None = None) -> Path:
    root = root or Path.cwd()
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise FileNotFoundError(f"exercise pack not found: {p}")
        return p
    default = root / "out" / "exercise_pack.json"
    if default.exists():
        return default
    found = sorted((root / "out").glob("**/exercise_pack.json"), key=lambda p: p.stat().st_mtime, reverse=True) if (root / "out").exists() else []
    if not found:
        raise FileNotFoundError("no approved exercise found in out/; build one with /tabletop first, or pass --pack")
    return found[0]


def _tracker_candidates(root: Path) -> list[Path]:
    seen: list[Path] = []
    for folder, pattern in (("uploads", "*.xlsx"), ("uploads", "*.csv"), ("out", "**/decision_tracker*.xlsx"), ("out", "**/decisions.csv")):
        base = root / folder
        if base.exists():
            for p in base.glob(pattern):
                if p.name.startswith("~$"):
                    continue  # Office lock file: the tracker is still open in Excel
                if p not in seen:
                    seen.append(p)
    return sorted(seen, key=lambda p: p.stat().st_mtime, reverse=True)


def find_tracker(pack: dict, explicit: str | None = None, root: Path | None = None) -> tuple[Path, list[str]]:
    """Return (tracker path, notes). Auto-detect picks the newest filled tracker built for this exercise."""
    from .score_engine import read_tracker

    root = root or Path.cwd()
    notes: list[str] = []
    want = (pack.get("approval") or {}).get("outline_hash")
    if explicit:
        p = Path(explicit.strip().strip('"').strip("'"))
        if not p.exists():
            raise FileNotFoundError(f"tracker not found: {p}")
        t = read_tracker(p)
        got = (t.get("meta") or {}).get("outline_hash")
        if got and want and got != want:
            notes.append(f"warning: {p.name} was built for a different exercise ({(t.get('meta') or {}).get('title')}); scoring anyway because you named it")
        if not t["decisions"]:
            raise ValueError(f"{p.name} has no answers yet; fill in the yellow cells during the exercise, save, and run this again")
        return p, notes
    checked = []
    for p in _tracker_candidates(root):
        try:
            t = read_tracker(p)
        except Exception as exc:  # not a tracker, or unreadable
            checked.append(f"{p.relative_to(root)} (skipped: {exc})")
            continue
        got = (t.get("meta") or {}).get("outline_hash")
        if got and want and got != want:
            checked.append(f"{p.relative_to(root)} (built for a different exercise)")
            continue
        if not t["decisions"]:
            checked.append(f"{p.relative_to(root)} (no answers yet)")
            continue
        return p, notes
    detail = "; ".join(checked) if checked else "no trackers found in uploads/ or out/"
    raise FileNotFoundError(
        "could not find a filled tracker for this exercise. Save the filled decision_tracker.xlsx into the uploads folder "
        f"(or pass --tracker <file>) and run this again. Checked: {detail}")


def run_report(pack_path: str | None = None, tracker_path: str | None = None, out_dir: str | None = None,
               narrative_path: str | None = None, root: Path | None = None) -> dict:
    from .build.aar import build_aar, check_narrative
    from .build.exec_summary import build_content, build_exec_deck, build_exec_memo
    from .score_engine import score_tracker

    root = root or Path.cwd()
    pack_file = find_pack(pack_path, root)
    pack = read_json(pack_file)
    if not (pack.get("approval") or {}).get("approved"):
        raise ValueError(f"{pack_file} is not approved; approve the outline before scoring")
    tracker, notes = find_tracker(pack, tracker_path, root)
    narrative = read_json(narrative_path) if narrative_path else None
    out = Path(out_dir) if out_dir else root / "out" / "report"
    out.mkdir(parents=True, exist_ok=True)

    score = score_tracker(pack, tracker)
    write_json(out / "score.json", score)
    if narrative:
        bad = check_narrative(narrative, score, pack)
        if bad:
            raise ValueError(f"narrative contains numbers that the score and pack do not: {bad}")
    files = {
        "score": str(out / "score.json"),
        "after_action_report": str(build_aar(pack, score, out / "after_action_report.docx", narrative=narrative)),
        "executive_summary_slides": str(build_exec_deck(pack, score, out / "executive_summary.pptx", narrative=narrative)),
        "executive_summary_memo": str(build_exec_memo(pack, score, out / "executive_summary.docx", narrative=narrative)),
    }
    content = build_content(pack, score, narrative)
    return {"pack": str(pack_file), "tracker": str(tracker), "notes": notes, "files": files, "out": str(out),
            "headline": content["headline"], "rating": content["rating"], "percent": content["percent"],
            "risks": content["risks"], "asks": content["asks"], "summary": score["summary"]}
