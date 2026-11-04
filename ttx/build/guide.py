"""Facilitator guide (the script), python-docx.

Per inject: timing, slide number, host lines, decision forced and its owner,
what good looks like, where teams fail, expected actions as a checklist,
hints, probing questions, a "what the plan says" box, and the source finding
or labeled assumption. Ends with the clocks and their sources.
"""

from __future__ import annotations

from pathlib import Path

from docx.shared import Pt

from .docx_util import (
    banner, boxed, bullets, checkbox_list, kv, new_document, party_name, plan_box_lines, role_name, source_line, table,
)


def build_guide(pack: dict, path: str | Path, draft: bool = False) -> Path:
    org = pack.get("organization") or {}
    doc = new_document("Facilitator guide", pack.get("title"), draft=draft)
    banner(doc, pack)

    doc.add_heading("How to run this exercise", level=1)
    approval = pack.get("approval") or {}
    kv(doc, [
        ("Organization", org.get("name")),
        ("Scenario", (pack.get("scenario") or {}).get("summary")),
        ("Severity", f"Level {pack.get('severity_level')}"),
        ("Duration", f"{pack.get('duration_minutes')} minutes, {len(pack.get('injects', []))} injects"),
        ("Audience", pack.get("audience")),
        ("Attack path source", f"{(pack.get('seed') or {}).get('path_source')} ({(pack.get('seed') or {}).get('source')})"),
        ("Plan source", "uploaded organization plan" if (pack.get("org_plan") or {}).get("items") else "industry pack defaults (no plan uploaded)"),
        ("Approved", f"{approval.get('approved_by')} at {approval.get('approved_at')}" if approval.get("approved") else "NOT APPROVED"),
    ])
    bullets(doc, [
        "The deck is on the projector. You hold this guide (or host.html on a separate laptop). The slide number for each inject is printed below.",
        "Read the host lines as written. Then stay quiet and let the room work. Use hints only when the room stalls; use probing questions to test the plan.",
        "Record every decision in the decision tracker: what was decided, which role decided, how long it took, who was told, which expected actions happened.",
        "Do not add facts that are not in this guide. If the room asks something the guide does not answer, say the information is not yet known.",
    ])

    doc.add_heading("Timing", level=1)
    table(doc, ["Inject", "Time", "Slide", "Phase", "Title", "Minutes", "Decision owner"],
          [[j["order"], j.get("time_marker"), j.get("slide_number"), j.get("phase"), j.get("title"), j.get("time_budget_minutes"),
            role_name(pack, j.get("decision_owner_role"))] for j in pack.get("injects", [])],
          widths=[0.5, 0.6, 0.5, 1.0, 2.4, 0.7, 1.6])

    for inj in pack.get("injects", []):
        doc.add_page_break()
        doc.add_heading(f"Inject {inj['order']}: {inj.get('title')}", level=1)
        p = doc.add_paragraph()
        r = p.add_run(f"{inj.get('time_marker')}  |  Slide {inj.get('slide_number')}  |  {str(inj.get('phase')).title()}  |  {inj.get('time_budget_minutes')} minutes")
        r.bold = True
        doc.add_heading("Host lines (read aloud)", level=3)
        for line in inj.get("host_lines") or []:
            q = doc.add_paragraph()
            qr = q.add_run(f"“{line}”")
            qr.italic = True
            qr.font.size = Pt(11.5)
        doc.add_heading("What happens", level=3)
        doc.add_paragraph(inj.get("what_happens") or "")
        kv(doc, [
            ("Who receives it", ", ".join(inj.get("recipients") or [])),
            ("Decision forced", inj.get("decision_forced")),
            ("Decision owner", role_name(pack, inj.get("decision_owner_role")) + (
                f" (also acceptable: {', '.join(role_name(pack, r) for r in inj.get('acceptable_owner_roles') or [])})" if inj.get("acceptable_owner_roles") else "")),
            ("Plan timing commitment", f"{inj['plan_commitment_minutes']} minutes" if inj.get("plan_commitment_minutes") else "none stated"),
        ])
        heading, lines, fill = plan_box_lines(pack, inj)
        boxed(doc, heading, lines, fill)
        doc.add_heading("What good looks like", level=3)
        doc.add_paragraph(inj.get("what_good_looks_like") or "")
        doc.add_heading("Where teams usually fail", level=3)
        doc.add_paragraph(inj.get("where_teams_fail") or "")
        doc.add_heading("Expected actions (tick as they happen; ids go in the tracker)", level=3)
        checkbox_list(doc, [f"[{a['id']}] {a['text']}  ({a.get('source')})" for a in inj.get("expected_actions") or []])
        if inj.get("expected_notifications"):
            doc.add_heading("Expected notifications", level=3)
            checkbox_list(doc, [f"[{n}] {party_name(pack, n)}" for n in inj["expected_notifications"]])
        doc.add_heading("Hints (only if the room stalls)", level=3)
        bullets(doc, inj.get("hints") or [])
        doc.add_heading("Probing questions", level=3)
        bullets(doc, inj.get("probing_questions") or [])
        flags = inj.get("flags") or {}
        notes = []
        if flags.get("conflicting_information"):
            notes.append("This inject delivers conflicting information on purpose. Do not resolve it for the room.")
        if flags.get("business_tradeoff"):
            notes.append("This inject forces a business tradeoff. Push for a named decision maker and a recorded reason.")
        if flags.get("plan_silent"):
            notes.append("This inject tests a point the plan is silent on. Record what the room decides; it becomes a plan gap in the report.")
        if flags.get("starts_clock"):
            notes.append("The notification clocks start at this inject. Ask for an owner and a planned notification time for each clock and record them on the tracker's Clocks sheet.")
        if notes:
            boxed(doc, "Facilitator notes", notes)
        doc.add_heading("Source", level=3)
        doc.add_paragraph(source_line(pack, inj))

    doc.add_page_break()
    doc.add_heading("Notification clocks in this exercise", level=1)
    doc.add_paragraph("Every deadline below comes from the pack's clocks.yaml with its source. Researched-tier clocks must be verified before the exercise is relied on.")
    rows = []
    for c in pack.get("clocks", []):
        dl = f"{c['deadline_hours']:g} h" if c.get("deadline_hours") is not None else (f"{c['deadline_business_days']} business days" if c.get("deadline_business_days") is not None else "no fixed number")
        rows.append([c["id"], c.get("regulator"), dl, c.get("tier"), str(c.get("verified_date")), c.get("citation"), c.get("source_url")])
    table(doc, ["Clock", "Regulator", "Deadline", "Tier", "Checked", "Citation", "Source"], rows, font_size=8)
    for c in pack.get("clocks", []):
        p = doc.add_paragraph()
        r = p.add_run(f"{c['id']}: ")
        r.bold = True
        p.add_run(f"{c.get('deadline_text')}. Trigger: {c.get('trigger')}.")

    doc.add_heading("Hot wash questions", level=1)
    bullets(doc, (pack.get("hot_wash") or {}).get("questions") or [])

    if (pack.get("seed") or {}).get("assumptions"):
        doc.add_heading("Labeled assumptions", level=1)
        bullets(doc, [f"{a['id']}: {a['text']}" for a in pack["seed"]["assumptions"]])

    path = Path(path)
    doc.save(path)
    return path
