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
        label = (proc.get("label") or "").replace("Plan is silent on: ", "")
        if label.startswith("No plan uploaded") and label.endswith(")") and "(" in label:
            return label[label.rfind("(") + 1:-1]  # "... do not cover (public statement approval)"
        return label or None
    return None


def gap_kind(gap: dict) -> str:
    """Classify a gap from score_engine by what went wrong (for grouping lessons)."""
    if gap.get("clock_id"):
        return "clock"
    if gap["label"] in {"plan", "technical"}:
        return gap["label"]
    f = gap.get("finding") or ""
    if "the decision was made by" in f:
        return "owner"
    if f.startswith("Not notified"):
        return "notify"
    if f.startswith("Slower than"):
        return "timing"
    return "steps"


def _join(items: list[str], limit: int = 3) -> str:
    items = list(dict.fromkeys(i for i in items if i))
    more = len(items) - limit
    items = items[:limit]
    if not items:
        return ""
    if more > 0:
        return ", ".join(items) + f", and {more} more"
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def lessons(pack: dict, score: dict) -> tuple[list[str], list[str]]:
    """Return (what worked, what to improve), each a short list of plain sentences built only from the score."""
    worked, improve = _lessons(pack, score)
    return worked, [text for _, text in improve]


def _lessons(pack: dict, score: dict) -> tuple[list[str], list[tuple[str, str]]]:
    """Like lessons(), but each improvement comes with the gap kind it summarizes."""
    s = score["summary"]
    gaps = score.get("gaps", [])
    clocks = score.get("clocks", [])
    titles = {r["inject_id"]: r["title"] for r in score.get("injects", [])}
    seed = pack.get("seed") or {}

    worked: list[str] = []
    for dim, avg in s["dimension_averages"].items():
        if avg is not None and avg >= 2.5:
            worked.append(AREA_LABELS.get(dim, dim) + ".")
    full = [r for r in score.get("injects", []) if r.get("reached") and r.get("max") and r.get("total") == r.get("max")]
    if full:
        worked.append(f"Handled exactly as expected: {_join([r['title'] for r in full], 2)}.")
    numeric = [c for c in clocks if c["status"] != "no_fixed_deadline"]
    if numeric and all(c["status"] == "met" for c in numeric):
        worked.append("Every notification deadline had an owner and a plan that meets it.")
    if not worked:
        worked.append(f"The team reached a decision at {s['injects_scored']} of {s['injects_total']} injects.")

    by_kind: dict[str, list[dict]] = {}
    for g in gaps:
        by_kind.setdefault(gap_kind(g), []).append(g)
    improve: list[tuple[str, str]] = []
    if by_kind.get("clock"):
        names = [next((c["name"] for c in clocks if c["clock_id"] == g["clock_id"]), g["clock_id"]) for g in by_kind["clock"]]
        improve.append(("clock", f"Regulatory notices were not ready: {_join(names, 2)}. Name an owner and pre-draft each notice now."))
    topics = []
    for g in by_kind.get("plan", []):
        t = _gap_topic(pack, g)
        if t:
            topics.append(t.lower())
    if topics:
        improve.append(("plan", f"The plan is silent on {_join(topics, 2)}; decide who owns it and write it down."))
    if by_kind.get("owner"):
        n = len(by_kind["owner"])
        improve.append(("owner", f"{'A decision was' if n == 1 else f'{n} decisions were'} made by someone other than the named owner "
                       f"({_join([titles.get(g['inject_id'], g['inject_id']) for g in by_kind['owner']], 2)}). Settle who holds that authority before the next incident."))
    if by_kind.get("notify"):
        parties = []
        for g in by_kind["notify"]:
            parties += [p.strip() for p in g["finding"].split(":", 1)[1].rstrip(".").split(",")]
        improve.append(("notify", f"Key parties were not told when expected: {_join(parties, 3)}."))
    if by_kind.get("timing"):
        improve.append(("timing", f"Escalation was slower than the plan commits to ({_join([titles.get(g['inject_id'], g['inject_id']) for g in by_kind['timing']], 2)})."))
    if by_kind.get("steps"):
        steps = by_kind["steps"]
        injects = {g["inject_id"] for g in steps}
        improve.append(("steps", f"{len(steps)} expected step{'s were' if len(steps) != 1 else ' was'} skipped across {len(injects)} decision{'s' if len(injects) != 1 else ''}; add them to the incident checklist."))
    if by_kind.get("technical"):
        assets = [(seed.get(p) or {}).get("asset") for p in ("entry", "pivot", "target")
                  if any(g.get("finding_id") == (seed.get(p) or {}).get("finding_id") for g in by_kind["technical"])]
        improve.append(("technical", f"The weaknesses the attacker used are still open on {_join([a for a in assets if a], 3)}."))
    return worked[:3], improve[:5]


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
    worked, improve_kinds = _lessons(pack, score)
    demo = score.get("demo") or {}
    return {
        "demo_label": demo.get("label") or "",
        "demo_note": demo.get("note") or "",
        "worked": worked,
        "improve": [text for _, text in improve_kinds],
        # the memo's regulatory exposure section already lists unready notices
        "improve_without_notices": [text for kind, text in improve_kinds if kind != "clock"],
        "organization": org.get("name") or "The organization",
        "short_name": org.get("short_name") or org.get("name") or "The organization",
        "date": str(when),
        "scenario": (pack.get("scenario") or {}).get("summary") or "",
        "scenario_short": f"{(pack.get('scenario') or {}).get('family', 'incident').replace('_', ' ').title()} scenario, severity {pack.get('severity_level')}, {pack.get('duration_minutes')} minutes",
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

    from .deck import H, NAVY, RED, TEAL, W, WHITE, _bullets, _frame, _notes, _rect, _text

    c = build_content(pack, score, narrative)
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    rgb = lambda hexs: RGBColor.from_string(hexs)  # noqa: E731

    def frame(title, number, **kw):
        slide = _frame(prs, title, number, pack, False, **kw)
        if c["demo_label"]:
            _text(slide, Inches(6.4), Inches(7.0), Inches(5.5), Inches(0.35), c["demo_label"].upper(), size=12, bold=True, color=RED, align=PP_ALIGN.RIGHT)
        return slide

    # 1 title
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _rect(s, 0, 0, W, H, NAVY)
    _rect(s, 0, Inches(4.6), W, Inches(0.08), TEAL)
    _text(s, Inches(0.8), Inches(1.4), Inches(11.5), Inches(0.5), "EXECUTIVE SUMMARY", size=16, bold=True, color=RGBColor(0x9F, 0xD8, 0xE0))
    _text(s, Inches(0.8), Inches(2.0), Inches(11.7), Inches(1.4), "Cyber incident readiness: tabletop exercise results", size=36, bold=True, color=WHITE)
    _text(s, Inches(0.8), Inches(3.5), Inches(11.5), Inches(0.8), f"{c['organization']}  |  {c['date']}", size=20, color=RGBColor(0xC9, 0xD3, 0xE3))
    _text(s, Inches(0.8), Inches(4.9), Inches(11.5), Inches(0.6), c["scenario_short"], size=16, color=WHITE)
    if c["demo_label"]:
        _rect(s, Inches(0.8), Inches(5.8), Inches(11.7), Inches(0.9), RED)
        _text(s, Inches(1.0), Inches(5.88), Inches(11.3), Inches(0.75), f"{c['demo_label'].upper()}. {c['demo_note']}", size=13, bold=True, color=WHITE)
    _notes(s, ["Purpose: what the exercise showed about our readiness, the regulatory exposure, and what we need leadership to decide."])

    # 2 bottom line
    s = frame("The bottom line", 2)
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
    s = frame("Regulatory exposure", 3, accent=rgb("B02418"))
    _text(s, Inches(0.8), Inches(1.5), Inches(11.8), Inches(0.6), c["exposure_line"], size=22, bold=True, color=NAVY)
    items = [e["text"] for e in c["exposure"]] or ["Every notification deadline was met, with a named owner."]
    _bullets(s, Inches(0.8), Inches(2.3), Inches(11.8), Inches(3.8), items[:5], size=19)
    if c["unverified_note"]:
        _text(s, Inches(0.8), Inches(6.3), Inches(11.8), Inches(0.5), c["unverified_note"], size=12, color=RGBColor(0x7A, 0x52, 0x00))

    # 4 top risks
    s = frame("What worries us most", 4)
    _bullets(s, Inches(0.8), Inches(1.6), Inches(11.8), Inches(5.0), c["risks"] or ["No significant risks surfaced in this exercise."], size=22)

    # 5 lessons learned
    s = frame("Lessons learned", 5)
    _rect(s, Inches(0.8), Inches(1.55), Inches(5.7), Inches(0.5), rgb("2E8B57"))
    _text(s, Inches(0.95), Inches(1.6), Inches(5.4), Inches(0.4), "What worked", size=17, bold=True, color=WHITE)
    _bullets(s, Inches(0.8), Inches(2.2), Inches(5.7), Inches(4.6), c["worked"], size=17)
    _rect(s, Inches(6.9), Inches(1.55), Inches(5.7), Inches(0.5), rgb("B02418"))
    _text(s, Inches(7.05), Inches(1.6), Inches(5.4), Inches(0.4), "What to improve", size=17, bold=True, color=WHITE)
    _bullets(s, Inches(6.9), Inches(2.2), Inches(5.7), Inches(4.6), c["improve"] or ["Nothing significant surfaced in this exercise."], size=15)
    _notes(s, ["Built from the score: areas rated Good are what worked; each improvement groups the gaps in the after-action report."])

    # 6 actions
    s = frame("What we are fixing, who owns it, and by when", 6)
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

    # 7 asks
    s = frame("Decisions we need from you", 7, accent=rgb("2E8B57"))
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

    if c["demo_label"]:
        from .docx_util import AMBER_FILL, boxed
        boxed(doc, c["demo_label"].upper(), ["Invented answers for a demonstration, not the result of a real exercise."], AMBER_FILL)
        spacer = doc.paragraphs[-1]._element  # boxed() adds a blank line; the memo needs the room
        spacer.getparent().remove(spacer)
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
    doc.add_paragraph().paragraph_format.space_after = Pt(0)

    doc.add_heading("Regulatory exposure", level=2)
    doc.add_paragraph(c["exposure_line"])
    for e in c["exposure"][:4]:
        doc.add_paragraph(e["text"], style="List Bullet")
    if c["unverified_note"]:
        q = doc.add_paragraph()
        qr = q.add_run(c["unverified_note"])
        qr.italic = True
        qr.font.size = Pt(9)

    # The memo stays on one page: lessons learned carry the risks here (the deck keeps both).
    doc.add_heading("Lessons learned", level=2)
    lt = doc.add_table(rows=2, cols=2)
    lt.style = "Table Grid"
    for i, (head, items, fill) in enumerate((("What worked", c["worked"], "2E8B57"),
                                             ("What to improve", c["improve_without_notices"][:3] or ["Nothing significant surfaced."], "B02418"))):
        hc, bc = lt.rows[0].cells[i], lt.rows[1].cells[i]
        shade(hc, fill)
        hr = hc.paragraphs[0].add_run(head)
        hr.bold = True
        hr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        for j, item in enumerate(items):
            para = bc.paragraphs[0] if j == 0 else bc.add_paragraph()
            para.add_run("\u2022 " + item).font.size = Pt(9)

    doc.add_heading("What we are fixing", level=2)
    # the top four fit on one page; the deck and the AAR carry the rest
    table(doc, ["Action", "Owner", "Due"], [[a["action"], a["owner"], a["due"]] for a in c["actions"][:4]], widths=[4.6, 1.5, 0.9], font_size=9)

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
