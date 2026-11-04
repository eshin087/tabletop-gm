"""After-action report (python-docx), built from score.json and exercise_pack.json.

Leads with the headline line, then scores, regulatory exposure, gaps with
labels, owners, and dates, the plan coverage map, the decision log, and an
evidence page an auditor, examiner, or insurer can accept.

An optional narrative.json (written by the scoring_aar skill) may replace the
headline and add an executive summary. Every number in it must already appear
in the score or the pack, so the model cannot introduce a figure.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from docx.shared import Pt

from .. import __version__
from .docx_util import NAVY, banner, boxed, bullets, kv, new_document, role_name, table, AMBER_FILL, SILENT_FILL, PLAN_FILL

STATUS_LABEL = {"met": "Met", "missed": "MISSED", "not_planned": "NOT PLANNED", "no_fixed_deadline": "No fixed deadline"}
COVERAGE_LABEL = {"followed": "Followed", "deviated": "Deviated", "not_reached": "Not reached", "not_covered": "Not covered"}
NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def check_narrative(narrative: dict, score: dict, pack: dict) -> list[str]:
    """Return numbers in the narrative that appear nowhere in the score or the pack."""
    haystack = json.dumps(score, default=str) + json.dumps(pack, default=str)
    known = set(NUM_RE.findall(haystack))
    known |= {n.rstrip("0").rstrip(".") for n in known if "." in n}
    bad = []
    text = " ".join([narrative.get("headline") or ""] + list(narrative.get("summary") or []))
    for n in NUM_RE.findall(text):
        if n not in known and n.rstrip("0").rstrip(".") not in known:
            bad.append(n)
    return sorted(set(bad))


def _dim(v):
    return "n/a" if v is None else v


def build_aar(pack: dict, score: dict, path: str | Path, narrative: dict | None = None,
              log: dict | None = None, log_file: str | Path | None = None) -> Path:
    if narrative:
        bad = check_narrative(narrative, score, pack)
        if bad:
            raise ValueError(f"narrative contains numbers that the score and pack do not: {bad}")
    org = pack.get("organization") or {}
    exercise = (pack.get("intake") or {}).get("exercise") or {}
    s = score["summary"]
    doc = new_document("After-action report", pack.get("title"))
    banner(doc, pack)

    # headline
    p = doc.add_paragraph()
    r = p.add_run((narrative or {}).get("headline") or score["headline"])
    r.bold = True
    r.font.size = Pt(15)
    r.font.color.rgb = NAVY
    for para in (narrative or {}).get("summary") or []:
        doc.add_paragraph(para)

    doc.add_heading("At a glance", level=1)
    table(doc, ["Measure", "Result"], [
        ["Overall score", f"{s['total_score']} of {s['max_score']} ({s['percent']}%)"],
        ["Decisions scored", f"{s['injects_scored']} of {s['injects_total']} injects"],
        ["Notification clocks", f"{s['clocks_met']} met, {s['clocks_missed']} missed, {s['clocks_not_planned']} not planned, {s['clocks_no_fixed_deadline']} with no fixed deadline"],
        ["Gaps", ", ".join(f"{sum(1 for g in score['gaps'] if g['label'] == lab)} {lab}" for lab in ("plan", "people", "technical"))],
        ["Expected actions came from", "the organization's uploaded plan" if score.get("plan_source") == "org_plan" else "industry pack defaults (no plan uploaded)"],
    ], widths=[2.0, 4.6])
    table(doc, ["Dimension", "Average (1 to 3)"], [[score["dimension_labels"][d], _dim(v)] for d, v in s["dimension_averages"].items()], widths=[3.0, 2.0])

    doc.add_heading("Scores by decision", level=1)
    rows = []
    for res in score["injects"]:
        sc = res["scores"]
        rows.append([res["inject_id"], res["title"], _dim(sc["right_owner"]), _dim(sc["timely"]), _dim(sc["escalation_notification"]),
                     _dim(sc["documented"]), _dim(sc["followed_plan"]), f"{res.get('total', 0)}/{res.get('max', 0)}" if res["reached"] else "not reached"])
    table(doc, ["Inject", "Title", "Owner", "Timely", "Escalation", "Documented", "Plan", "Total"], rows,
          widths=[0.5, 2.3, 0.6, 0.6, 0.8, 0.8, 0.5, 0.7], font_size=8.5)

    doc.add_heading("Regulatory exposure", level=1)
    doc.add_paragraph("Each clock comes from the industry pack with its source and verification tier. Planned hours are what the team committed to during the exercise.")
    crow = []
    for c in score["clocks"]:
        margin = "" if c.get("margin_hours") is None else (f"+{c['margin_hours']:g} h" if c["margin_hours"] >= 0 else f"{c['margin_hours']:g} h")
        dl = "none" if c.get("deadline_hours") is None else f"{c['deadline_hours']:g} h" + (" (business days, approx.)" if c.get("deadline_is_business_day_approximation") else "")
        crow.append([c["name"], dl, "" if c.get("planned_notify_hours") is None else f"{c['planned_notify_hours']:g} h",
                     STATUS_LABEL.get(c["status"], c["status"]), margin, role_name(pack, c.get("owner_role")) or "none named", c.get("tier")])
    table(doc, ["Clock", "Limit", "Planned", "Status", "Margin", "Owner", "Tier"], crow, widths=[2.4, 0.9, 0.7, 0.9, 0.7, 1.2, 0.8], font_size=8.5)
    internal = [c for c in score["clocks"] if c.get("internal_deadline_hours") is not None]
    for c in internal:
        boxed(doc, f"Internal standard: {c['name']}",
              [f"The plan (section {c.get('internal_section')}) sets {c['internal_deadline_hours']:g} hours: “{c.get('internal_quote')}”",
               "Met" if c.get("internal_met") else ("Missed" if c.get("internal_met") is False else "Not evaluated")], PLAN_FILL)
    researched = [c for c in score["clocks"] if c.get("tier") != "verified"]
    if researched:
        boxed(doc, "Unverified clocks", ["These clocks are researched tier and were not human-verified on the date shown: " +
                                         ", ".join(c["clock_id"] for c in researched) + ". Verify each against its source before relying on this section."], AMBER_FILL)

    doc.add_heading("Gaps and fixes", level=1)
    doc.add_paragraph("Plan gap: the plan is silent or unclear, fix the document. People gap: the plan says one thing and the team did another, fix with training or role clarity. Technical gap: an open finding on the exercised path, fix the system.")
    for label, title in (("plan", "Plan gaps"), ("people", "People gaps"), ("technical", "Technical gaps")):
        items = [g for g in score["gaps"] if g["label"] == label]
        doc.add_heading(f"{title} ({len(items)})", level=2)
        if not items:
            doc.add_paragraph("None.")
            continue
        table(doc, ["Id", "Inject", "Finding", "Citation", "Fix", "Owner", "Due"],
              [[g["id"], g.get("inject_id") or "", g["finding"], g["citation"], g["fix"], g["owner"], g["due"]] for g in items],
              widths=[0.55, 0.4, 1.75, 1.4, 1.4, 0.75, 0.65], font_size=8)

    doc.add_heading("Plan coverage map", level=1)
    cov = score.get("coverage") or {}
    if not cov.get("present"):
        doc.add_paragraph(cov.get("note") or "No plan uploaded.")
    else:
        counts = cov["counts"]
        doc.add_paragraph(
            f"{counts['followed']} plan items followed, {counts['deviated']} deviated from, {counts['not_reached']} not reached, "
            f"{counts['not_covered']} not covered by this scenario. {counts['silent_exercised']} silent topics exercised, "
            f"{counts['silent_not_exercised']} silent topics not exercised.")
        table(doc, ["Section", "Items", "Followed", "Deviated", "Not reached", "Not covered"],
              [[sec["section"], sec["items"], sec["followed"], sec["deviated"], sec["not_reached"], sec["not_covered"]] for sec in cov["sections"]],
              widths=[1.0, 0.7, 0.8, 0.8, 0.9, 0.9], font_size=9)
        table(doc, ["Section", "Item", "Plan says", "Status", "Injects"],
              [[r["section"], r["item_id"], r["label"], COVERAGE_LABEL.get(r["status"], r["status"]), ", ".join(r["injects"])] for r in cov["rows"]],
              widths=[0.7, 0.5, 3.4, 1.0, 1.0], font_size=8)
        if cov.get("silent"):
            doc.add_heading("Where the plan is silent", level=2)
            for g in cov["silent"]:
                boxed(doc, f"{g['gap_id']}: {g['topic']} ({'exercised' if g['status'] == 'silent_exercised' else 'not exercised in this scenario'})", [g.get("note") or ""], SILENT_FILL)

    doc.add_heading("Decision log", level=1)
    injects = {j["id"]: j for j in pack.get("injects", [])}
    for res in score["injects"]:
        inj = injects.get(res["inject_id"], {})
        doc.add_heading(f"{res['inject_id']}: {res['title']}", level=3)
        kv(doc, [
            ("Decision", res.get("decision") or "not recorded"),
            ("Decided by", role_name(pack, res.get("decided_by_role")) or "not recorded"),
            ("Expected owner", role_name(pack, inj.get("decision_owner_role"))),
            ("Procedure tested", (inj.get("procedure_tested") or {}).get("label")),
        ])
        bullets(doc, [f"{score['dimension_labels'][d]}: {_dim(res['scores'][d])} ({res['reasons'].get(d, '')})" for d in res["scores"]])

    # evidence page
    doc.add_page_break()
    doc.add_heading("Evidence page", level=1)
    approval = pack.get("approval") or {}
    seed = pack.get("seed") or {}
    kv(doc, [
        ("Organization", org.get("name")),
        ("Exercise date", exercise.get("date")),
        ("Location", exercise.get("location")),
        ("Facilitator", exercise.get("facilitator")),
        ("Executive sponsor", exercise.get("sponsor")),
        ("Scenario", (pack.get("scenario") or {}).get("summary")),
        ("Severity, length, injects", f"Level {pack.get('severity_level')}, {pack.get('duration_minutes')} minutes, {len(pack.get('injects', []))} injects"),
        ("Outline approval", f"{approval.get('approved_by')} at {approval.get('approved_at')}" if approval.get("approved") else "NOT APPROVED"),
        ("Approved outline hash", approval.get("outline_hash")),
        ("Exercise pack hash (scored)", score["inputs"]["exercise_pack_hash"]),
        ("Tracker", f"{score['inputs']['tracker_file']} (sha256 {score['inputs']['tracker_sha256']})"),
        ("Attendance", "attendance_signin.xlsx and signoff_sheet.docx from the same build"),
        ("Generator", f"Tabletop GM ttx {__version__}; deterministic scoring, rubric below"),
    ])
    doc.add_heading("Documents exercised", level=2)
    docs = (pack.get("org_plan") or {}).get("source_documents") or []
    if docs:
        table(doc, ["Id", "Document", "Version", "File"], [[d.get("id"), d.get("title"), d.get("version"), d.get("filename")] for d in docs])
        doc.add_paragraph("Every plan statement in this report is a verbatim quote that the validator confirmed exists in the source document.")
    else:
        doc.add_paragraph("No organization documents were uploaded.")
    doc.add_heading("Requirements this exercise supports", level=2)
    reqs = pack.get("exercise_requirements") or []
    if reqs:
        table(doc, ["Requirement", "Citation", "Tier", "Source"], [[r.get("name"), r.get("citation"), r.get("tier"), r.get("source_url")] for r in reqs], font_size=8)
    doc.add_heading("Notification clocks and verification status", level=2)
    table(doc, ["Clock", "Citation", "Tier", "Checked", "Source"],
          [[c["clock_id"], c.get("citation"), c.get("tier"), str(c.get("verified_date")), c.get("source_url")] for c in score["clocks"]], font_size=7.5)
    if researched:
        doc.add_paragraph("Unverified (researched tier): " + ", ".join(c["clock_id"] for c in researched) + ".")
    doc.add_heading("Exposure data behind the scenario", level=2)
    rows = []
    for part in ("entry", "pivot", "target"):
        node = seed.get(part) or {}
        rows.append([part, node.get("asset"), node.get("finding_id") or node.get("assumption") or "", node.get("cve") or "", node.get("rule")])
    table(doc, ["Step", "Asset", "Finding or assumption", "CVE", "Selection rule"], rows)
    kv(doc, [("Data source", seed.get("source")), ("Path source", seed.get("path_source"))])
    if seed.get("assumptions"):
        bullets(doc, [f"{a['id']}: {a['text']}" for a in seed["assumptions"]])
    doc.add_heading("Scoring rubric", level=2)
    table(doc, ["Dimension", "3", "2", "1"],
          [[score["dimension_labels"][d], rub[3], rub[2], rub[1]] for d, rub in ((d, {int(k): v for k, v in score["rubric"][d].items()}) for d in score["rubric"])],
          font_size=8)

    # live mode: the decision timeline, rendered from the append-only log without change
    if log is not None:
        from ..decision_log import session_summary, timeline

        doc.add_page_break()
        doc.add_heading("Appendix: decision timeline", level=1)
        doc.add_paragraph(session_summary(log, log_file))
        doc.add_paragraph("Every logged entry in order: planned and unplanned decisions, injects presented or skipped, clock answers, "
                          "and facilitator notes. Unplanned decisions and skipped injects are shown but not scored. A corrected entry "
                          "appears twice: the original marked superseded, and the correction naming who asked for it.")
        table(doc, ["#", "Wall clock", "Scenario", "Inject", "Entry", "Owner", "Score"],
              [[r["n"], r["wall_clock"], r["scenario_time"], r["inject_id"], r["entry"], r["owner"], r["score"]] for r in timeline(log, pack, score)],
              widths=[0.35, 1.25, 0.6, 0.5, 2.9, 0.9, 0.7], font_size=8)
    path = Path(path)
    doc.save(path)
    return path
