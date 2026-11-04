"""Small python-docx helpers shared by the Word generators."""

from __future__ import annotations

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Inches

NAVY = RGBColor(0x1F, 0x2A, 0x44)
GREY = RGBColor(0x55, 0x5F, 0x6D)
RED = RGBColor(0xB0, 0x24, 0x18)
AMBER_FILL = "FFF4CE"
PLAN_FILL = "EAF1FB"
HEADER_FILL = "1F2A44"
SILENT_FILL = "FDECEA"


def new_document(title: str, subtitle: str | None = None, draft: bool = False, landscape: bool = False) -> Document:
    doc = Document()
    styles = doc.styles
    styles["Normal"].font.name = "Calibri"
    styles["Normal"].font.size = Pt(10.5)
    for name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)):
        st = styles[name]
        st.font.name = "Calibri"
        st.font.size = Pt(size)
        st.font.color.rgb = NAVY
    section = doc.sections[0]
    if landscape:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = section.page_height, section.page_width
    for s in doc.sections:
        s.left_margin = s.right_margin = Inches(0.8)
        s.top_margin = s.bottom_margin = Inches(0.7)
    if draft:
        p = doc.add_paragraph()
        r = p.add_run("DRAFT: built from an unapproved outline. Not for use in an exercise.")
        r.bold = True
        r.font.color.rgb = RED
    t = doc.add_paragraph()
    run = t.add_run(title)
    run.bold = True
    run.font.size = Pt(22)
    run.font.color.rgb = NAVY
    if subtitle:
        s = doc.add_paragraph()
        sr = s.add_run(subtitle)
        sr.font.size = Pt(12)
        sr.font.color.rgb = GREY
    footer = doc.sections[0].footer.paragraphs[0]
    footer.text = ("DRAFT  |  " if draft else "") + "Built by Tabletop GM from the approved exercise pack. Synthetic sample data where noted."
    footer.runs[0].font.size = Pt(8)
    footer.runs[0].font.color.rgb = GREY
    return doc


def shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def table(doc, headers: list[str], rows: list[list], widths: list[float] | None = None, font_size: float = 9.5):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(str(h))
        run.bold = True
        run.font.size = Pt(font_size)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade(cell, HEADER_FILL)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run("" if val is None else str(val))
            run.font.size = Pt(font_size)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return t


def boxed(doc, heading: str, lines: list[str], fill: str = PLAN_FILL):
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    cell = t.rows[0].cells[0]
    shade(cell, fill)
    cell.text = ""
    p = cell.paragraphs[0]
    r = p.add_run(heading)
    r.bold = True
    r.font.size = Pt(10)
    for line in lines:
        q = cell.add_paragraph()
        qr = q.add_run(line)
        qr.font.size = Pt(10)
    doc.add_paragraph()
    return t


def banner(doc, pack: dict) -> None:
    b = pack.get("banner") or {}
    if not b.get("show"):
        return
    boxed(doc, "Verify before exercise", [b.get("text") or "", "Researched-tier clocks: " + ", ".join(b.get("researched_clock_ids") or [])], AMBER_FILL)


def bullets(doc, items: list[str]) -> None:
    for item in items:
        doc.add_paragraph(str(item), style="List Bullet")


def checkbox_list(doc, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph()
        p.add_run("☐  ").font.size = Pt(11)
        p.add_run(str(item))


def kv(doc, pairs: list[tuple[str, str]]) -> None:
    for k, v in pairs:
        p = doc.add_paragraph()
        r = p.add_run(f"{k}: ")
        r.bold = True
        p.add_run("" if v is None else str(v))


def signature_line(doc, label: str) -> None:
    doc.add_paragraph()
    p = doc.add_paragraph("_" * 46 + "        " + "_" * 18)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    q = doc.add_paragraph()
    r = q.add_run(f"{label}" + " " * 60 + "Date")
    r.font.size = Pt(9)
    r.font.color.rgb = GREY


def role_name(pack: dict, role_id: str | None) -> str:
    for r in pack.get("roles", []):
        if r["id"] == role_id:
            return r.get("name") or role_id
    return role_id or ""


def party_name(pack: dict, party_id: str) -> str:
    for p in pack.get("notify_parties", []):
        if p["id"] == party_id:
            return p.get("name") or party_id
    return party_id


def source_line(pack: dict, inj: dict) -> str:
    src = inj.get("source") or {}
    seed = pack.get("seed") or {}
    if src.get("type") == "finding":
        for part in ("entry", "pivot", "target"):
            node = seed.get(part) or {}
            if node.get("finding_id") == src.get("ref"):
                bits = [f"Finding {node['finding_id']}", f"asset {node.get('asset')}"]
                if node.get("cve"):
                    bits.append(node["cve"])
                if node.get("vpr") is not None:
                    bits.append(f"VPR {node['vpr']}")
                if node.get("kev"):
                    bits.append("CISA KEV")
                bits.append(f"{part} step, rule {node.get('rule')}")
                return ", ".join(bits) + f" (source: {seed.get('source')})"
        return f"Finding {src.get('ref')}"
    for a in list(seed.get("assumptions") or []) + list(pack.get("assumptions") or []):
        if a.get("id") == src.get("ref"):
            return f"Assumption {a['id']}: {a.get('text')}"
    return f"Assumption {src.get('ref')}"


def plan_box_lines(pack: dict, inj: dict) -> tuple[str, list[str], str]:
    proc = inj.get("procedure_tested") or {}
    if proc.get("type") == "org_plan":
        return ("What the plan says", [proc.get("label") or "", f"“{proc.get('quote')}”"], PLAN_FILL)
    if proc.get("type") == "plan_silent":
        gap = next((g for g in (pack.get("org_plan") or {}).get("gaps", []) if g.get("id") == proc.get("ref")), None)
        lines = [proc.get("label") or "The plan is silent here."]
        if gap and gap.get("note"):
            lines.append(gap["note"])
        lines.append("Coach to the decision, not to a document: ask who would decide and how it would be recorded.")
        return ("What the plan says: nothing", lines, SILENT_FILL)
    return ("What the pack default says (no plan uploaded)", [proc.get("label") or ""], PLAN_FILL)
