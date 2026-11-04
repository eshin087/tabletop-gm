"""Participant handout (python-docx). No spoilers: no injects, systems, findings, or answers."""

from __future__ import annotations

from pathlib import Path

from .docx_util import bullets, kv, new_document, table


def build_handout(pack: dict, path: str | Path, draft: bool = False) -> Path:
    org = pack.get("organization") or {}
    exercise = (pack.get("intake") or {}).get("exercise") or {}
    doc = new_document("Participant handout", f"{org.get('name')} cybersecurity tabletop exercise", draft=draft)
    kv(doc, [
        ("Date", exercise.get("date")),
        ("Location", exercise.get("location")),
        ("Length", f"{pack.get('duration_minutes')} minutes"),
        ("Facilitator", exercise.get("facilitator")),
    ])
    doc.add_heading("Why we are here", level=1)
    bullets(doc, pack.get("objectives") or [])
    doc.add_heading("Ground rules", level=1)
    bullets(doc, pack.get("ground_rules") or [])
    doc.add_heading("Roles at the table", level=1)
    table(doc, ["Role", "Played by", "Authority in this exercise"],
          [[r.get("name"), "", r.get("authority") or ""] for r in pack.get("roles", [])], widths=[2.2, 1.8, 3.0])
    doc.add_heading("Contact list (fill in before the exercise)", level=1)
    doc.add_paragraph("Write the real names and numbers you would use tonight. Gaps here are findings.")
    table(doc, ["Role or party", "Name", "Phone", "Backup"],
          [[r.get("name"), "", "", ""] for r in pack.get("roles", [])] +
          [[p.get("name"), "", "", ""] for p in pack.get("notify_parties", [])], widths=[2.6, 1.6, 1.4, 1.4])
    doc.add_heading("Notes", level=1)
    for inj in pack.get("injects", []):
        doc.add_paragraph(f"Update {inj['order']} ({inj.get('time_marker')})")
        for _ in range(3):
            doc.add_paragraph("_" * 92)
    path = Path(path)
    doc.save(path)
    return path
