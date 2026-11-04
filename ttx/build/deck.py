"""Deck for the room (python-pptx).

Slide order: title, ground rules, objectives, roles, scenario setup, one slide
per inject (numbered to match inject.slide_number so the host console and the
facilitator guide stay aligned), hot wash, next steps. The audience never sees
expected actions, good answers, or failure modes; host lines go in the
speaker notes.
"""

from __future__ import annotations

import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

NAVY = RGBColor(0x1F, 0x2A, 0x44)
TEAL = RGBColor(0x1B, 0x7F, 0x8C)
LIGHT = RGBColor(0xF4, 0xF6, 0xF9)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREY = RGBColor(0x55, 0x5F, 0x6D)
AMBER = RGBColor(0xFF, 0xF4, 0xCE)
AMBER_TEXT = RGBColor(0x7A, 0x52, 0x00)
RED = RGBColor(0xB0, 0x24, 0x18)
PHASE_COLORS = {
    "detection": RGBColor(0x2E, 0x6F, 0xB7),
    "escalation": RGBColor(0x8A, 0x4F, 0xB5),
    "containment": RGBColor(0xC2, 0x5B, 0x12),
    "recovery": RGBColor(0x2E, 0x8B, 0x57),
    "notification": RGBColor(0xB0, 0x24, 0x18),
}
W, H = Inches(13.333), Inches(7.5)


def _text(slide, left, top, width, height, text, size=18, bold=False, color=NAVY, align=PP_ALIGN.LEFT, font="Calibri"):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    lines = text if isinstance(text, list) else [text]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        run = p.add_run()
        run.text = str(line)
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = font
    return box


def _bullets(slide, left, top, width, height, items, size=18, color=NAVY):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(8)
        run = p.add_run()
        run.text = "•  " + str(item)
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.name = "Calibri"
    return box


def _rect(slide, left, top, width, height, fill, line=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
    shp.shadow.inherit = False
    return shp


def _frame(prs, title: str, number: int, pack: dict, draft: bool, accent=TEAL, kicker: str | None = None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _rect(slide, 0, 0, W, Inches(1.15), NAVY)
    _rect(slide, 0, Inches(1.15), W, Inches(0.07), accent)
    if kicker:
        _text(slide, Inches(0.6), Inches(0.12), Inches(10), Inches(0.35), kicker, size=12, color=RGBColor(0xC9, 0xD3, 0xE3))
    _text(slide, Inches(0.6), Inches(0.38) if kicker else Inches(0.28), Inches(11.4), Inches(0.7), title, size=28, bold=True, color=WHITE)
    org = (pack.get("organization") or {}).get("name") or ""
    _text(slide, Inches(0.6), Inches(7.0), Inches(9), Inches(0.35), f"{org}  |  Tabletop exercise  |  For exercise use only", size=10, color=GREY)
    _text(slide, Inches(12.0), Inches(7.0), Inches(0.8), Inches(0.35), str(number), size=10, color=GREY, align=PP_ALIGN.RIGHT)
    if draft:
        _text(slide, Inches(9.6), Inches(7.0), Inches(2.3), Inches(0.35), "DRAFT", size=12, bold=True, color=RED, align=PP_ALIGN.RIGHT)
    return slide


def _notes(slide, lines: list[str]) -> None:
    slide.notes_slide.notes_text_frame.text = "\n".join(lines)


def build_deck(pack: dict, path: str | Path, draft: bool = False) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    org = pack.get("organization") or {}
    intake = pack.get("intake") or {}
    exercise = intake.get("exercise") or {}
    n = 0

    # 1. title
    n += 1
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _rect(s, 0, 0, W, H, NAVY)
    _rect(s, 0, Inches(4.6), W, Inches(0.08), TEAL)
    _text(s, Inches(0.8), Inches(1.4), Inches(11.5), Inches(0.5), "CYBERSECURITY TABLETOP EXERCISE", size=16, bold=True, color=RGBColor(0x9F, 0xD8, 0xE0))
    _text(s, Inches(0.8), Inches(2.0), Inches(11.5), Inches(1.6), org.get("name") or "Organization", size=44, bold=True, color=WHITE)
    _text(s, Inches(0.8), Inches(3.4), Inches(11.5), Inches(1.0),
          f"{(pack.get('scenario') or {}).get('family', 'incident').title()} scenario  |  Severity {pack.get('severity_level')}  |  {pack.get('duration_minutes')} minutes",
          size=20, color=RGBColor(0xC9, 0xD3, 0xE3))
    meta = [x for x in (exercise.get("date"), exercise.get("location")) if x]
    _text(s, Inches(0.8), Inches(4.9), Inches(11.5), Inches(0.6), "  |  ".join(str(m) for m in meta), size=16, color=WHITE)
    if draft:
        _text(s, Inches(0.8), Inches(5.6), Inches(11.5), Inches(0.6), "DRAFT: built from an unapproved outline", size=18, bold=True, color=RGBColor(0xFF, 0x8A, 0x80))
    if (pack.get("banner") or {}).get("show"):
        _text(s, Inches(0.8), Inches(6.4), Inches(11.7), Inches(0.8),
              "Notification deadlines shown in this exercise include researched-tier clocks that must be verified against their sources before the exercise is relied on.",
              size=11, color=RGBColor(0xFF, 0xE0, 0x8A))
    _notes(s, ["Welcome the room. Introduce the facilitator, the sponsor, and the purpose: practice the organization's own plan under realistic pressure.",
               "Remind the room that the scenario is built from the organization's own exposure data and its own written procedures."])

    # 2. ground rules
    n += 1
    s = _frame(prs, "Ground rules", n, pack, draft)
    _bullets(s, Inches(0.8), Inches(1.6), Inches(11.8), Inches(5.2), pack.get("ground_rules") or [], size=20)
    _notes(s, ["Read each rule aloud. Ask the room to confirm phones are down except for role-play."])

    # 3. objectives
    n += 1
    s = _frame(prs, "Objectives", n, pack, draft)
    _bullets(s, Inches(0.8), Inches(1.6), Inches(11.8), Inches(5.2), pack.get("objectives") or [], size=20)
    _notes(s, ["These objectives are the scoring frame for the after-action report."])

    # 4. roles
    n += 1
    s = _frame(prs, "Who is at the table", n, pack, draft)
    roles = pack.get("roles") or []
    half = (len(roles) + 1) // 2
    _bullets(s, Inches(0.8), Inches(1.6), Inches(6.0), Inches(5.3), [r["name"] for r in roles[:half]], size=17)
    _bullets(s, Inches(6.9), Inches(1.6), Inches(6.0), Inches(5.3), [r["name"] for r in roles[half:]], size=17)
    _notes(s, ["Confirm who is playing each role. Anyone absent: name who would act for them, and note it on the sign-in sheet."])

    # 5. setup (no spoilers about the path)
    n += 1
    s = _frame(prs, "Scenario setup", n, pack, draft)
    setup = [
        f"{org.get('name')}: {org.get('description') or ''}".strip(),
        f"Data the organization holds: {', '.join(intake.get('data_types') or [])}",
        f"Where it operates: {', '.join((intake.get('countries') or []) + (intake.get('states') or []))}",
        "It is an ordinary weekday evening. Staffing is normal for the shift.",
        "You will receive updates (injects). Each one asks for a decision. Say who decides, what they decide, and who they tell.",
    ]
    _bullets(s, Inches(0.8), Inches(1.6), Inches(11.8), Inches(5.0), setup, size=19)
    _notes(s, ["Do not reveal the attack path or the systems involved before the injects do."])

    # injects
    for inj in pack.get("injects", []):
        n += 1
        if inj.get("slide_number") and inj["slide_number"] != n:
            raise ValueError(f"inject {inj['id']} expects slide {inj['slide_number']} but the deck is at slide {n}")
        color = PHASE_COLORS.get(inj.get("phase"), TEAL)
        s = _frame(prs, inj.get("title") or inj["id"], n, pack, draft, accent=color,
                   kicker=f"INJECT {inj['order']}  |  {inj.get('time_marker')}  |  {str(inj.get('phase')).upper()}")
        _text(s, Inches(0.8), Inches(1.55), Inches(11.8), Inches(2.7), inj.get("what_happens") or "", size=21, color=NAVY)
        _rect(s, Inches(0.8), Inches(4.45), Inches(11.8), Inches(1.45), LIGHT, line=color)
        _text(s, Inches(1.05), Inches(4.55), Inches(11.3), Inches(0.4), "DECISION", size=12, bold=True, color=color)
        _text(s, Inches(1.05), Inches(4.9), Inches(11.3), Inches(1.0), inj.get("decision_forced") or "", size=19, bold=True, color=NAVY)
        recips = ", ".join(inj.get("recipients") or [])
        _text(s, Inches(0.8), Inches(5.95), Inches(11.8), Inches(0.45), f"Reaches: {recips}", size=13, color=GREY)
        if as_clock_slide(inj):
            _clock_strip(s, pack)
        notes = ["HOST LINES (read aloud):"] + [f"  {line}" for line in inj.get("host_lines") or []]
        notes += ["", "PROBING QUESTIONS:"] + [f"  {q}" for q in inj.get("probing_questions") or []]
        notes += ["", f"Facilitator guide: inject {inj['order']}. Host console: slide {n}."]
        _notes(s, notes)

    # hot wash
    n += 1
    s = _frame(prs, "Hot wash", n, pack, draft)
    _bullets(s, Inches(0.8), Inches(1.6), Inches(11.8), Inches(5.2), (pack.get("hot_wash") or {}).get("questions") or [], size=20)
    _notes(s, ["Give each question two or three minutes. Capture answers in the tracker notes column for the after-action report."])

    # next steps
    n += 1
    s = _frame(prs, "Next steps", n, pack, draft)
    _bullets(s, Inches(0.8), Inches(1.6), Inches(11.8), Inches(5.2), pack.get("next_steps") or [], size=20)
    _notes(s, ["Collect the sign-in sheet and the sponsor sign-off before people leave."])

    path = Path(path)
    prs.save(path)
    return path


def as_clock_slide(inj: dict) -> bool:
    return bool((inj.get("flags") or {}).get("starts_clock"))


def _clock_strip(slide, pack: dict) -> None:
    """On the inject that starts the clocks, show the tightest deadlines (from the pack, never invented)."""
    # chained clocks run from another notice, not from this moment, so they are not "running" yet
    clocks = [c for c in pack.get("clocks", []) if (c.get("deadline_hours") is not None or c.get("deadline_business_days") is not None)
              and not c.get("after_clock")]
    clocks.sort(key=lambda c: (c.get("deadline_hours") if c.get("deadline_hours") is not None else c["deadline_business_days"] * 33.6, c["id"]))
    items = []
    seen = set()
    for c in clocks:
        if c.get("deadline_hours") is not None:
            h = c["deadline_hours"]
            when = f"{int(h // 24)} days" if h >= 72 and h % 24 == 0 else f"{h:g} hours"
        else:
            when = f"{c['deadline_business_days']} business days"
        who = re.sub(r"\s*\([^)]*\)", "", c.get("regulator") or c["name"]).strip()
        if (who, when) in seen:
            continue
        seen.add((who, when))
        tier = " (verify)" if c.get("tier") != "verified" else ""
        items.append(f"{who}: {when}{tier}")
        if len(items) == 3:
            break
    if items:
        _rect(slide, Inches(0.8), Inches(6.4), Inches(11.8), Inches(0.58), AMBER)
        _text(slide, Inches(0.95), Inches(6.42), Inches(11.6), Inches(0.55), "Clocks now running:  " + "   |   ".join(items), size=11, color=AMBER_TEXT)
