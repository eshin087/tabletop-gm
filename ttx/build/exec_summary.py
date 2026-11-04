"""Executive summary for a senior management audience: a short deck and a one-page memo.

Both are built from the same content, computed here from score.json and the
exercise pack, so they never disagree with each other or with the after-action
report. Plain language, no finding IDs, no rubric detail: the AAR carries that.
Every number comes from the score; an optional narrative.json may replace the
headline, and build_aar's number check applies to it.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..score_engine import hours_words

RATINGS = [(85.0, "Strong", "2E8B57"), (70.0, "Adequate", "C98A00"), (0.0, "Needs work", "B02418")]
AREA_LABELS = {
    "right_owner": "The right people made the calls",
    "timely": "We acted in time",
    "escalation_notification": "We escalated and told the right parties",
    "documented": "We kept a record",
    "followed_plan": "We followed our own plan",
}


def rating_for(percent: float) -> tuple[str, str]:
    for floor, label, color in RATINGS:
        if percent >= floor:
            return label, color
    return RATINGS[-1][1], RATINGS[-1][2]


def area_status(avg: float | None) -> tuple[str, str]:
    if avg is None:
        return "Not tested", "8A94A6"
    if avg >= 2.5:
        return "Good", "2E8B57"
    if avg >= 2.0:
        return "Mixed", "C98A00"
    return "Weak", "B02418"


def _role(pack: dict, role_id: str | None) -> str:
    for r in pack.get("roles", []):
        if r["id"] == role_id:
            return r.get("name") or role_id
    return role_id or "Unassigned"


def _gap_topic(pack: dict, gap: dict) -> str | None:
    inj = next((j for j in pack.get("injects", []) if j["id"] == gap.get("inject_id")), None)
    proc = (inj or {}).get("procedure_tested") or {}
    if proc.get("type") == "plan_silent":
        g = next((x for x in (pack.get("org_plan") or {}).get("gaps", []) if x.get("id") == proc.get("ref")), None)
        if g:
            return g.get("topic")
        return (proc.get("label") or "").replace("Plan is silent on: ", "") or None
    return None


def build_content(pack: dict, score: dict, narrative: dict | None = None) -> dict:
    s = score["summary"]
    org = pack.get("organization") or {}
    exercise = (pack.get("intake") or {}).get("exercise") or {}
    label, color = rating_for(float(s["percent"]))
    seed = pack.get("seed") or {}

    areas = []
    for dim, avg in s["dimension_averages"].items():
        status, scolor = area_status(avg)
        areas.append({"label": AREA_LABELS.get(dim, dim), "status": status, "color": scolor, "average": avg})

    clocks = score.get("clocks", [])
    exposure = []
    for c in sorted([c for c in clocks if c["status"] == "missed"], key=lambda c: c["margin_hours"]):
        exposure.append({"text": f"{c['name']}: planned too late, missed by {hours_words(abs(c['margin_hours']))}.", "severity": "high"})
    for c in [c for c in clocks if c["status"] == "not_planned"]:
        owner = "" if c.get("owner_role") else " and no one owns it"
        exposure.append({"text": f"{c['name']}: the team did not plan this notice{owner}.", "severity": "high"})
    met = sum(1 for c in clocks if c["status"] == "met")
    numeric = sum(1 for c in clocks if c["status"] != "no_fixed_deadline")
    exposure_line = (f"{met} of {numeric} notification deadlines met." if numeric else "No notification deadlines applied.")
    unverified = [c for c in clocks if c.get("tier") != "verified"]

    gaps = score.get("gaps", [])
    risks: list[str] = []
    if exposure:
        risks.append(exposure[0]["text"])
    seen_topics = set()
    for g in gaps:
        if g["label"] == "plan":
            topic = _gap_topic(pack, g)
            if topic and topic.lower() not in seen_topics:
                seen_topics.add(topic.lower())
                risks.append(f"Our plan does not say who decides: {topic.lower()}.")
    entry = seed.get("entry") or {}
    if entry.get("finding_id") and entry.get("kev"):
        risks.append(f"The attack's entry point, an actively exploited weakness on {entry.get('asset')} ({entry.get('cve')}), is still open.")
    owner_misses = [g for g in gaps if g["label"] == "people" and "the decision was made by" in g["finding"]]
    if owner_misses:
        risks.append("Some decisions were made by someone other than the person the plan names.")
    risks = risks[:3]

    def priority(g: dict) -> tuple:
        if g.get("clock_id"):
            return (0, g["due"])
        if g["label"] == "plan":
            return (1, g["due"])
        if g["label"] == "technical":
            return (2, g["due"])
        return (3, g["due"])

    actions = []
    for g in sorted(gaps, key=priority):
        text = g["fix"]
        if g.get("clock_id"):
            name = next((c["name"] for c in clocks if c["clock_id"] == g["clock_id"]), g["clock_id"])
            text = f"Name an owner and pre-draft the notice for: {name}."
        elif g["label"] == "plan" and _gap_topic(pack, g):
            text = f"Update the plan to name who decides {_gap_topic(pack, g).lower()}."
        elif g["label"] == "technical":
            node = next((seed.get(p) for p in ("entry", "pivot", "target") if (seed.get(p) or {}).get("finding_id") == g.get("finding_id")), {}) or {}
            text = f"Fix the open weakness on {node.get('asset')} ({node.get('cve') or 'see report'}) and confirm it in the next scan."
        if any(a["action"] == text for a in actions):
            continue
        actions.append({"action": text, "owner": g["owner"], "due": g["due"]})
        if len(actions) == 5:
            break

    asks = []
    plan_topics = [t for t in seen_topics]
    if plan_topics:
        asks.append(f"Approve updating the incident response plan to name who decides {', '.join(sorted(plan_topics))}.")
    kev_open = [p for p in ("entry", "pivot", "target") if (seed.get(p) or {}).get("finding_id") and (seed.get(p) or {}).get("kev")]
    if kev_open:
        asks.append(f"Prioritize fixing the {len(kev_open)} actively exploited weaknesses on the tested attack path.")
    if exposure:
        asks.append("Confirm an owner for every regulatory notice before the next incident, not during it.")
    if unverified:
        asks.append("Ask counsel to confirm the notification deadlines used in this exercise; they have not been independently verified.")
    asks.append("Schedule the next exercise for next quarter, aimed at the parts of the plan this one did not cover.")

    when = exercise.get("date") or date.today().isoformat()
    short = org.get("short_name") or org.get("name") or "The organization"
    plain = f"{short}'s readiness to handle a serious cyber incident is {label.lower()}: {s['percent']}% across {s['injects_scored']} decisions."
    if risks:
        plain += f" The biggest exposure: {risks[0]}"
    return {
        "organization": org.get("name") or "The organization",
        "short_name": org.get("short_name") or org.get("name") or "The organization",
        "date": str(when),
        "scenario": (pack.get("scenario") or {}).get("summary") or "",
        "scenario_short": f"{(pack.get('scenario') or {}).get('family', 'incident').title()} scenario, severity {pack.get('severity_level')}, {pack.get('duration_minutes')} minutes",
        "headline": (narrative or {}).get("headline") or plain,
        "percent": s["percent"],
        "rating": label,
        "rating_color": color,
        "decisions_scored": s["injects_scored"],
        "areas": areas,
        "exposure": exposure,
        "exposure_line": exposure_line,
        "unverified_note": "Notification deadlines in this exercise are researched but not yet independently verified." if unverified else "",
        "risks": risks,
        "actions": actions,
        "asks": asks,
        "gap_counts": {lab: sum(1 for g in gaps if g["label"] == lab) for lab in ("plan", "people", "technical")},
    }


# --------------------------------------------------------------------------- #
# Deck
# --------------------------------------------------------------------------- #

def build_exec_deck(pack: dict, score: dict, path: str | Path, narrative: dict | None = None) -> Path:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    from .deck import H, NAVY, TEAL, W, WHITE, _bullets, _frame, _notes, _rect, _text

    c = build_content(pack, score, narrative)
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    rgb = lambda hexs: RGBColor.from_string(hexs)  # noqa: E731

    # 1 title
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _rect(s, 0, 0, W, H, NAVY)
    _rect(s, 0, Inches(4.6), W, Inches(0.08), TEAL)
    _text(s, Inches(0.8), Inches(1.4), Inches(11.5), Inches(0.5), "EXECUTIVE SUMMARY", size=16, bold=True, color=RGBColor(0x9F, 0xD8, 0xE0))
    _text(s, Inches(0.8), Inches(2.0), Inches(11.7), Inches(1.4), "Cyber incident readiness: tabletop exercise results", size=36, bold=True, color=WHITE)
    _text(s, Inches(0.8), Inches(3.5), Inches(11.5), Inches(0.8), f"{c['organization']}  |  {c['date']}", size=20, color=RGBColor(0xC9, 0xD3, 0xE3))
    _text(s, Inches(0.8), Inches(4.9), Inches(11.5), Inches(0.6), c["scenario_short"], size=16, color=WHITE)
    _notes(s, ["Purpose: what the exercise showed about our readiness, the regulatory exposure, and what we need leadership to decide."])

    # 2 bottom line
    s = _frame(prs, "The bottom line", 2, pack, False)
    _text(s, Inches(0.8), Inches(1.5), Inches(11.8), Inches(1.3), c["headline"], size=20, bold=True, color=NAVY)
    _rect(s, Inches(0.8), Inches(3.05), Inches(3.4), Inches(2.6), rgb(c["rating_color"]))
    _text(s, Inches(0.8), Inches(3.25), Inches(3.4), Inches(0.5), "OVERALL READINESS", size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    _text(s, Inches(0.8), Inches(3.75), Inches(3.4), Inches(1.0), c["rating"], size=36, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    _text(s, Inches(0.8), Inches(4.75), Inches(3.4), Inches(0.6), f"{c['percent']}% across {c['decisions_scored']} decisions", size=14, color=WHITE, align=PP_ALIGN.CENTER)
    y = 3.05
    for a in c["areas"]:
        _rect(s, Inches(4.6), Inches(y + 0.08), Inches(0.28), Inches(0.28), rgb(a["color"]))
        _text(s, Inches(5.0), Inches(y), Inches(5.6), Inches(0.45), a["label"], size=15, color=NAVY)
        _text(s, Inches(10.7), Inches(y), Inches(1.9), Inches(0.45), a["status"], size=15, bold=True, color=rgb(a["color"]))
        y += 0.52
    _notes(s, ["Rating thresholds: Strong 85% and up, Adequate 70 to 84%, Needs work below 70%. Area status: Good 2.5 and up on a 3-point scale, Mixed 2.0 to 2.4, Weak below 2.0."])

    # 3 regulatory exposure
    s = _frame(prs, "Regulatory exposure", 3, pack, False, accent=rgb("B02418"))
    _text(s, Inches(0.8), Inches(1.5), Inches(11.8), Inches(0.6), c["exposure_line"], size=22, bold=True, color=NAVY)
    items = [e["text"] for e in c["exposure"]] or ["Every notification deadline was met, with a named owner."]
    _bullets(s, Inches(0.8), Inches(2.3), Inches(11.8), Inches(3.8), items[:5], size=19)
    if c["unverified_note"]:
        _text(s, Inches(0.8), Inches(6.3), Inches(11.8), Inches(0.5), c["unverified_note"], size=12, color=RGBColor(0x7A, 0x52, 0x00))

    # 4 top risks
    s = _frame(prs, "What worries us most", 4, pack, False)
    _bullets(s, Inches(0.8), Inches(1.6), Inches(11.8), Inches(5.0), c["risks"] or ["No significant risks surfaced in this exercise."], size=22)

    # 5 actions
    s = _frame(prs, "What we are fixing, who owns it, and by when", 5, pack, False)
    rows = len(c["actions"]) + 1
    tbl = s.shapes.add_table(rows, 3, Inches(0.8), Inches(1.6), Inches(11.8), Inches(0.5 * rows)).table
    tbl.columns[0].width, tbl.columns[1].width, tbl.columns[2].width = Inches(7.6), Inches(2.6), Inches(1.6)
    for i, h in enumerate(("Action", "Owner", "Due")):
        cell = tbl.cell(0, i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        para = cell.text_frame.paragraphs[0]
        para.runs[0].font.bold = True
        para.runs[0].font.size = Pt(15)
        para.runs[0].font.color.rgb = WHITE
    for r, a in enumerate(c["actions"], start=1):
        for i, v in enumerate((a["action"], a["owner"], a["due"])):
            cell = tbl.cell(r, i)
            cell.text = str(v)
            cell.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
    _notes(s, ["The after-action report lists every gap with its citation; these are the highest-priority fixes."])

    # 6 asks
    s = _frame(prs, "Decisions we need from you", 6, pack, False, accent=rgb("2E8B57"))
    _bullets(s, Inches(0.8), Inches(1.6), Inches(11.8), Inches(5.0), c["asks"], size=21)

    path = Path(path)
    prs.save(path)
    return path


# --------------------------------------------------------------------------- #
# One-page memo
# --------------------------------------------------------------------------- #

def build_exec_memo(pack: dict, score: dict, path: str | Path, narrative: dict | None = None) -> Path:
    from docx.shared import Inches, Pt, RGBColor

    from .docx_util import NAVY, new_document, shade, table

    c = build_content(pack, score, narrative)
    doc = new_document("Executive summary: cyber incident readiness", f"{c['organization']}  |  Tabletop exercise, {c['date']}")
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Inches(0.6)
    doc.styles["Normal"].font.size = Pt(10)

    p = doc.add_paragraph()
    r = p.add_run("Bottom line. ")
    r.bold = True
    p.add_run(c["headline"])

    t = doc.add_table(rows=1, cols=2)
    t.style = "Table Grid"
    left, right = t.rows[0].cells
    shade(left, c["rating_color"])
    left.text = ""
    lr = left.paragraphs[0].add_run(f"Overall readiness: {c['rating']}\n")
    lr.bold = True
    lr.font.size = Pt(14)
    lr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    lr2 = left.paragraphs[0].add_run(f"{c['percent']}% across {c['decisions_scored']} decisions")
    lr2.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    right.text = ""
    for i, a in enumerate(c["areas"]):
        para = right.paragraphs[0] if i == 0 else right.add_paragraph()
        run = para.add_run(f"{a['status']}: ")
        run.bold = True
        run.font.color.rgb = RGBColor.from_string(a["color"])
        para.add_run(a["label"])
    left.width, right.width = Inches(2.4), Inches(4.5)
    doc.add_paragraph()

    doc.add_heading("Regulatory exposure", level=2)
    doc.add_paragraph(c["exposure_line"])
    for e in c["exposure"][:4]:
        doc.add_paragraph(e["text"], style="List Bullet")
    if c["unverified_note"]:
        q = doc.add_paragraph()
        qr = q.add_run(c["unverified_note"])
        qr.italic = True
        qr.font.size = Pt(9)

    doc.add_heading("What worries us most", level=2)
    for risk in c["risks"] or ["No significant risks surfaced in this exercise."]:
        doc.add_paragraph(risk, style="List Bullet")

    doc.add_heading("What we are fixing", level=2)
    table(doc, ["Action", "Owner", "Due"], [[a["action"], a["owner"], a["due"]] for a in c["actions"]], widths=[4.6, 1.5, 0.9], font_size=9)

    doc.add_heading("Decisions we need from you", level=2)
    for ask in c["asks"]:
        doc.add_paragraph(ask, style="List Number")

    note = doc.add_paragraph()
    nr = note.add_run("The full after-action report has every decision, score, citation, and the evidence page for auditors.")
    nr.italic = True
    nr.font.size = Pt(9)
    path = Path(path)
    doc.save(path)
    return path
