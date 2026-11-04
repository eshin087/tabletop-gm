"""Deliverable generators. Every output is built from exercise_pack.json only.

build_all refuses an unapproved or modified pack unless allow_draft is set, in
which case every document is watermarked DRAFT. No generator makes a network
or model call.
"""

from __future__ import annotations

from pathlib import Path

from ..validators import check_approval, validate_exercise_pack

GENERATORS = ["deck", "guide", "handout", "tracker", "signin", "signoff"]


def build_all(pack: dict, out_dir: str | Path, only: list[str] | None = None, allow_draft: bool = False) -> dict[str, str]:
    gate = check_approval(pack)
    if not gate.ok and not allow_draft:
        raise ValueError("; ".join(gate.errors))
    check = validate_exercise_pack(pack)
    if not check.ok:
        raise ValueError("exercise pack fails validation: " + "; ".join(check.errors))
    draft = not gate.ok
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    wanted = only or GENERATORS
    unknown = [w for w in wanted if w not in GENERATORS]
    if unknown:
        raise ValueError(f"unknown generator(s) {unknown}; choose from {GENERATORS}")

    from . import deck, guide, handout, signin, tracker

    built: dict[str, str] = {}
    if "deck" in wanted:
        built["deck"] = str(deck.build_deck(pack, out / "deck.pptx", draft=draft))
    if "guide" in wanted:
        built["facilitator_guide"] = str(guide.build_guide(pack, out / "facilitator_guide.docx", draft=draft))
    if "handout" in wanted:
        built["participant_handout"] = str(handout.build_handout(pack, out / "participant_handout.docx", draft=draft))
    if "tracker" in wanted:
        built["decision_tracker"] = str(tracker.build_tracker(pack, out / "decision_tracker.xlsx", draft=draft))
    if "signin" in wanted:
        built["attendance"] = str(signin.build_attendance(pack, out / "attendance_signin.xlsx", draft=draft))
    if "signoff" in wanted:
        built["signoff"] = str(signin.build_signoff(pack, out / "signoff_sheet.docx", draft=draft))
    return built
