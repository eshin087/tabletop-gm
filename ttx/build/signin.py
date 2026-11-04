"""Attendance sheet (openpyxl) and sign-off sheet (python-docx): audit evidence."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from .docx_util import banner, bullets, kv, new_document, signature_line, table

THIN = Side(style="thin", color="999999")


def build_attendance(pack: dict, path: str | Path, draft: bool = False, rows: int = 40) -> Path:
    org = pack.get("organization") or {}
    exercise = (pack.get("intake") or {}).get("exercise") or {}
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance"
    ws.append([("DRAFT  " if draft else "") + f"Attendance: {pack.get('title')}"])
    ws.append([f"Organization: {org.get('name')}", None, f"Date: {exercise.get('date') or ''}", None, f"Location: {exercise.get('location') or ''}"])
    ws.append([])
    headers = ["#", "Name", "Title", "Role played in exercise", "Department", "Time in", "Time out", "Signature"]
    ws.append(headers)
    ws["A1"].font = Font(bold=True, size=14)
    for i, _ in enumerate(headers, start=1):
        c = ws.cell(row=4, column=i)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F2A44")
    for i in range(1, rows + 1):
        ws.append([i] + [None] * (len(headers) - 1))
    for row in ws.iter_rows(min_row=4, max_row=4 + rows):
        for cell in row:
            cell.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
            cell.alignment = Alignment(vertical="center")
    for col, width in zip("ABCDEFGH", (5, 28, 26, 30, 20, 10, 10, 28)):
        ws.column_dimensions[col].width = width
    for r in range(5, 5 + rows):
        ws.row_dimensions[r].height = 24

    wr = wb.create_sheet("Roles present")
    wr.append(["Role", "Present (name)", "Absent: who acted instead"])
    for c in wr[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F2A44")
    for r in pack.get("roles", []):
        wr.append([r.get("name"), None, None])
    for col, width in zip("ABC", (42, 30, 34)):
        wr.column_dimensions[col].width = width
    path = Path(path)
    wb.save(path)
    return path


def build_signoff(pack: dict, path: str | Path, draft: bool = False) -> Path:
    org = pack.get("organization") or {}
    exercise = (pack.get("intake") or {}).get("exercise") or {}
    approval = pack.get("approval") or {}
    doc = new_document("Exercise sign-off", pack.get("title"), draft=draft)
    banner(doc, pack)
    doc.add_heading("Scope", level=1)
    kv(doc, [
        ("Organization", org.get("name")),
        ("Date", exercise.get("date")),
        ("Location", exercise.get("location")),
        ("Scenario", (pack.get("scenario") or {}).get("summary")),
        ("Severity and length", f"Level {pack.get('severity_level')}, {pack.get('duration_minutes')} minutes, {len(pack.get('injects', []))} injects"),
        ("Phases exercised", ", ".join(dict.fromkeys(j.get("phase") for j in pack.get("injects", [])))),
        ("Outline approved by", f"{approval.get('approved_by')} on {approval.get('approved_at')} (hash {str(approval.get('outline_hash'))[:16]})" if approval.get("approved") else "NOT APPROVED"),
    ])
    doc.add_heading("Documents exercised", level=1)
    docs = (pack.get("org_plan") or {}).get("source_documents") or []
    if docs:
        table(doc, ["Id", "Document", "Version", "File"], [[d.get("id"), d.get("title"), d.get("version"), d.get("filename")] for d in docs])
    else:
        doc.add_paragraph("No organization documents were uploaded; the exercise used the industry pack defaults.")
    doc.add_heading("Requirements this exercise supports", level=1)
    reqs = pack.get("exercise_requirements") or []
    if reqs:
        table(doc, ["Requirement", "Citation", "Frequency", "Tier"], [[r.get("name"), r.get("citation"), r.get("frequency"), r.get("tier")] for r in reqs])
    doc.add_heading("Notification clocks exercised", level=1)
    table(doc, ["Clock", "Citation", "Tier", "Checked on"], [[c["id"], c.get("citation"), c.get("tier"), str(c.get("verified_date"))] for c in pack.get("clocks", [])], font_size=8.5)
    doc.add_heading("Attestation", level=1)
    doc.add_paragraph(
        "We attest that the tabletop exercise described above was conducted on the date shown, with the participants recorded on the attendance sheet, "
        "using the scenario and documents listed. Findings and corrective actions are recorded in the after-action report.")
    signature_line(doc, "Facilitator (name and signature)")
    signature_line(doc, "Executive sponsor (name and signature)")
    signature_line(doc, "Plan owner (name and signature)")
    path = Path(path)
    doc.save(path)
    return path
