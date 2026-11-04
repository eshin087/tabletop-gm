"""After-action report (python-docx), built from score.json and exercise_pack.json.

Short by design. The body is what a reader needs to act:

  1. the headline and the overall result
  2. lessons learned: what worked and what to improve
  3. decision by decision, one line each
  4. the notification deadlines
  5. the action plan: every fix, grouped, with an owner and a due date

The appendix carries the detail an auditor, examiner, or insurer needs: the
scores by dimension, the plan coverage map, the gap register with citations,
and the evidence page.

An optional narrative.json (written by the scoring_aar skill) may replace the
headline and add a short summary. Every number in it must already appear in
the score or the pack, so the model cannot introduce a figure.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from docx.shared import Pt, RGBColor

from .. import __version__
from ..score_engine import hours_words
from ..common import REPO_ROOT
from .docx_util import AMBER_FILL, NAVY, SILENT_FILL, boxed, bullets, kv, new_document, role_name, shade, table

STATUS_LABEL = {"met": "Met", "missed": "MISSED", "not_planned": "NOT PLANNED", "no_fixed_deadline": "No fixed deadline"}
COVERAGE_LABEL = {"followed": "Followed", "deviated": "Deviated", "not_reached": "Not reached", "not_covered": "Not covered"}
TYPE_LABEL = {"plan": "Plan", "people": "People", "technical": "Technical"}
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


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


def _first_sentence(text: str) -> str:
    text = (text or "").strip()
    cut = text.find(". ")
    return (text[:cut] if cut > 0 else text.rstrip(".")).strip()


def _rel(path: str | None) -> str:
    try:
        return Path(path).resolve().relative_to(REPO_ROOT).as_posix()
    except (TypeError, ValueError):
        return str(path)


def _clock_result(c: dict) -> str:
    if c["status"] == "missed":
        return f"MISSED by {hours_words(abs(c['margin_hours']))}"
    return STATUS_LABEL.get(c["status"], c["status"])


def _after_colon(text: str) -> str:
    return (text.split(":", 1)[1] if ":" in text else text).strip().rstrip(".")


def _step_label(finding: str) -> str:
    """'Not done at this inject: Medical device isolation (IR Plan section 6.3: ...).' -> 'Medical device isolation'"""
    text = _after_colon(finding)
    cut = text.find(" (")
    return text[:cut] if cut > 0 else text


def short_issue(pack: dict, score: dict, gap: dict) -> str:
    """One plain line for a gap, for the body of the report (the appendix keeps the full finding)."""
    from .exec_summary import _gap_topic, gap_kind

    kind = gap_kind(gap)
    if kind == "owner":
        res = next((r for r in score.get("injects", []) if r["inject_id"] == gap.get("inject_id")), {})
        decided = role_name(pack, res.get("decided_by_role")) or "no one"
        return f"Decided by {decided}, not {gap['owner']}"
    if kind == "notify":
        return f"Not told: {_after_colon(gap['finding'])}"
    if kind == "steps":
        return f"Skipped: {_step_label(gap['finding'])}"
    if kind == "plan":
        topic = _gap_topic(pack, gap)
        if topic:
            return f"Plan is silent on {topic.lower()}"
    return _first_sentence(gap["finding"])


def action_plan(pack: dict, score: dict) -> list[dict]:
    """The fixes, grouped so each row is one thing to do. Order: notices, plan, technical, people.

    Each row: fix, why, label, owner, due (earliest), ids (the gap ids it closes).
    """
    from .exec_summary import _gap_topic, gap_kind

    seed = pack.get("seed") or {}
    titles = {r["inject_id"]: r["title"] for r in score.get("injects", [])}
    clocks = {c["clock_id"]: c for c in score.get("clocks", [])}
    rank = {"clock": 0, "plan": 1, "technical": 2, "owner": 3, "notify": 4, "timing": 5, "steps": 6}
    groups: dict[tuple, dict] = {}
    for g in score.get("gaps", []):
        kind = gap_kind(g)
        if kind == "clock":
            c = clocks.get(g["clock_id"], {})
            key = ("clock", g["id"])
            if c.get("status") == "missed":
                fix = f"Name an owner and pre-draft the notice: {c.get('name')}."
                why = (f"Planned at {hours_words(c.get('planned_notify_hours'))} against a limit of "
                       f"{hours_words(c.get('deadline_hours'))}.")
            elif c.get("status") == "not_planned":
                fix = f"Add this notice to the plan with an owner and a deadline: {c.get('name')}."
                why = "It applies, but nobody planned it" + ("." if c.get("owner_role") else " or owns it.")
            else:
                fix, why = g["fix"], g["finding"]
        elif kind == "plan" and _gap_topic(pack, g):
            topic = _gap_topic(pack, g).lower()
            key = ("plan", g["id"])
            fix = f"Write into the plan who decides {topic}, who is consulted, and how it is recorded."
            why = f"The plan is silent on it, so the room had to improvise ({titles.get(g.get('inject_id'), g.get('inject_id'))})."
        elif kind == "technical":
            node = next((seed.get(p) for p in ("entry", "pivot", "target")
                         if (seed.get(p) or {}).get("finding_id") == g.get("finding_id")), None) or {}
            key = ("technical", g["due"])
            fix = ("Patch or mitigate the open weaknesses on the attack path, confirm closure in the next scan, "
                   "and rerun this path next quarter if any stay open.")
            why = f"{node.get('asset')} ({node.get('cve') or 'see appendix'}{', actively exploited' if node.get('kev') else ''})"
        elif kind == "notify":
            key = ("notify",)
            fix = "Add these parties to the notification list, each with a named caller and a backup."
            why = f"{_after_colon(g['finding'])} ({g.get('inject_id')})"
        elif kind == "steps":
            key = ("steps",)
            fix = "Add the skipped steps to the incident checklist and rehearse them in the next exercise."
            why = f"{_step_label(g['finding'])} ({g.get('inject_id')})"
        elif kind == "timing":
            key, fix = ("timing",), g["fix"]
            why = f"{_after_colon(g['finding'])} ({g.get('inject_id')})"
        elif kind == "owner":
            key, fix = ("owner", g["id"]), g["fix"]
            why = short_issue(pack, score, g) + f" ({titles.get(g.get('inject_id'), g.get('inject_id'))})."
        else:
            key, fix, why = (kind, g["fix"]), g["fix"], g["finding"]
        grp = groups.setdefault(key, {"fix": fix, "label": g["label"], "rank": rank.get(kind, 7), "kind": kind,
                                      "why": [], "owners": [], "due": g["due"], "ids": []})
        grp["why"].append(why)
        if g["owner"] not in grp["owners"]:
            grp["owners"].append(g["owner"])
        grp["due"] = min(grp["due"], g["due"])
        grp["ids"].append(g["id"])

    def order(r: dict) -> tuple:
        first = r["ids"][0][3:]
        return (r["rank"], r["due"], int(first) if first.isdigit() else 0)

    rows = sorted(groups.values(), key=order)
    for r in rows:
        parts = list(dict.fromkeys(r["why"]))
        many = len(parts) > 1
        if r["kind"] == "technical":
            r["why"] = (", ".join(parts) + (" were" if many else " was") + " the exercised attack path and "
                        + ("are" if many else "is") + " still open.")
        elif r["kind"] == "notify":
            r["why"] = "Not told when expected: " + "; ".join(parts) + "."
        elif r["kind"] == "steps":
            r["why"] = "Skipped: " + "; ".join(parts) + "."
        elif r["kind"] == "timing":
            r["why"] = "Slower than the plan commits to: " + "; ".join(parts) + "."
        else:
            r["why"] = " ".join(parts)
        r["owner"] = ", ".join(r["owners"])
    return rows


def _two_column(doc, left_head: str, left: list[str], right_head: str, right: list[str]) -> None:
    t = doc.add_table(rows=2, cols=2)
    t.style = "Table Grid"
    for i, (head, items, fill) in enumerate(((left_head, left, "2E8B57"), (right_head, right, "B02418"))):
        hc, bc = t.rows[0].cells[i], t.rows[1].cells[i]
        shade(hc, fill)
        hr = hc.paragraphs[0].add_run(head)
        hr.bold = True
        hr.font.color.rgb = WHITE
        for j, item in enumerate(items):
            para = bc.paragraphs[0] if j == 0 else bc.add_paragraph()
            para.add_run("\u2022 " + item).font.size = Pt(9.5)
    doc.add_paragraph()


def build_aar(pack: dict, score: dict, path: str | Path, narrative: dict | None = None,
              log: dict | None = None, log_file: str | Path | None = None) -> Path:
    from .exec_summary import build_content, gap_kind

    if narrative:
        bad = check_narrative(narrative, score, pack)
        if bad:
            raise ValueError(f"narrative contains numbers that the score and pack do not: {bad}")
    c = build_content(pack, score, narrative)
    s = score["summary"]
    clocks = score.get("clocks", [])
    gaps = score.get("gaps", [])
    researched = [k for k in clocks if k.get("tier") != "verified"]

    doc = new_document("After-action report", f"{c['organization']}  |  {c['scenario_short']}  |  {c['date']}")
    if c["demo_label"]:
        boxed(doc, c["demo_label"].upper(), [c["demo_note"]], SILENT_FILL)
    if researched:
        boxed(doc, "Verify before relying on this report",
              [f"{len(researched)} of {len(clocks)} notification deadlines are researched but not yet human-verified. "
               "The appendix lists each one with its source."], AMBER_FILL)

    # 1. headline and result
    p = doc.add_paragraph()
    r = p.add_run(c["headline"])
    r.bold = True
    r.font.size = Pt(14)
    r.font.color.rgb = NAVY
    for para in (narrative or {}).get("summary") or []:
        doc.add_paragraph(para)

    numeric = [k for k in clocks if k["status"] != "no_fixed_deadline"]
    counts = {lab: sum(1 for g in gaps if g["label"] == lab) for lab in ("plan", "people", "technical")}
    t = table(doc, ["Readiness", "Score", "Decisions scored", "Deadlines met", "Gaps to fix"], [[
        c["rating"], f"{s['percent']}%", f"{s['injects_scored']} of {s['injects_total']}",
        f"{s['clocks_met']} of {len(numeric)}" if numeric else "none applied",
        f"{counts['plan']} plan, {counts['people']} people, {counts['technical']} technical"]],
        widths=[1.1, 0.8, 1.2, 1.1, 2.7], font_size=10)
    shade(t.rows[1].cells[0], c["rating_color"])
    t.rows[1].cells[0].paragraphs[0].runs[0].font.color.rgb = WHITE
    t.rows[1].cells[0].paragraphs[0].runs[0].bold = True

    # 2. lessons learned
    doc.add_heading("Lessons learned", level=1)
    _two_column(doc, "What worked", c["worked"], "What to improve", c["improve"] or ["Nothing significant surfaced in this exercise."])

    # 3. decision by decision
    doc.add_heading("Decision by decision", level=1)
    by_inject: dict[str, list[dict]] = {}
    for g in gaps:
        if g.get("inject_id") and gap_kind(g) != "clock":
            by_inject.setdefault(g["inject_id"], []).append(g)
    rows = []
    for res in score["injects"]:
        issues = by_inject.get(res["inject_id"], [])
        issue = short_issue(pack, score, issues[0]) if issues else "None"
        if len(issues) > 1:
            issue += f" (+{len(issues) - 1} more)"
        result = f"{res.get('total', 0)}/{res.get('max', 0)}" if res["reached"] else "Not reached"
        rows.append([res["inject_id"], res["title"], res.get("decision") or "not recorded",
                     role_name(pack, res.get("decided_by_role")) or "not recorded", result, issue])
    table(doc, ["#", "Inject", "What the team decided", "Decided by", "Score", "Main issue"], rows,
          widths=[0.35, 1.15, 2.1, 1.0, 0.5, 1.8], font_size=8.5)

    # 4. notification deadlines
    doc.add_heading("Notification deadlines", level=1)
    if clocks:
        table(doc, ["Notice", "Deadline", "Team planned", "Result", "Owner"],
              [[k["name"], hours_words(k.get("deadline_hours")) if k.get("deadline_hours") is not None else "none",
                hours_words(k.get("planned_notify_hours")) if k.get("planned_notify_hours") is not None else "not planned",
                _clock_result(k), role_name(pack, k.get("owner_role")) or "none named"] for k in clocks],
              widths=[2.9, 0.8, 0.95, 1.2, 1.05], font_size=8.5)
        for k in [k for k in clocks if k.get("internal_deadline_hours") is not None]:
            verdict = "met" if k.get("internal_met") else ("missed" if k.get("internal_met") is False else "not evaluated")
            doc.add_paragraph(f"{k['name']}: the plan's own standard (section {k.get('internal_section')}) is "
                              f"{k['internal_deadline_hours']:g} hours, {verdict}.")
    else:
        doc.add_paragraph("No notification deadlines applied to this scenario.")

    # 5. action plan
    doc.add_heading("Action plan", level=1)
    plan = action_plan(pack, score)
    if plan:
        table(doc, ["#", "Fix", "Why", "Type", "Owner", "Due", "Gaps"],
              [[str(i), r["fix"], r["why"], TYPE_LABEL.get(r["label"], r["label"]), r["owner"], r["due"], ", ".join(r["ids"])]
               for i, r in enumerate(plan, start=1)],
              widths=[0.3, 1.9, 2.05, 0.6, 0.85, 0.75, 0.55], font_size=8)
    else:
        doc.add_paragraph("No gaps were recorded.")

    _appendix(doc, pack, score, researched)
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


def _appendix(doc, pack: dict, score: dict, researched: list[dict]) -> None:
    org = pack.get("organization") or {}
    exercise = (pack.get("intake") or {}).get("exercise") or {}
    doc.add_page_break()
    doc.add_heading("Appendix: detail for auditors", level=1)
    doc.add_paragraph("The scoring detail, plan coverage, citations, and evidence behind the report above.")

    # A. scores
    doc.add_heading("A. Scores by decision", level=2)
    rows = []
    for res in score["injects"]:
        sc = res["scores"]
        rows.append([res["inject_id"], _dim(sc["right_owner"]), _dim(sc["timely"]), _dim(sc["escalation_notification"]),
                     _dim(sc["documented"]), _dim(sc["followed_plan"]), f"{res.get('total', 0)}/{res.get('max', 0)}" if res["reached"] else "not reached"])
    avgs = score["summary"]["dimension_averages"]
    rows.append(["Average", _dim(avgs.get("right_owner")), _dim(avgs.get("timely")), _dim(avgs.get("escalation_notification")),
                 _dim(avgs.get("documented")), _dim(avgs.get("followed_plan")),
                 f"{score['summary']['total_score']}/{score['summary']['max_score']}"])
    table(doc, ["Inject", "Owner", "Timely", "Escalation", "Documented", "Plan", "Total"], rows,
          widths=[0.8, 0.8, 0.8, 0.9, 1.0, 0.7, 0.9], font_size=8.5)
    doc.add_paragraph("Each dimension is scored 1 to 3 using the rubric in section E; n/a means the dimension did not apply. "
                      + ("Expected actions came from the organization's uploaded plan." if score.get("plan_source") == "org_plan"
                         else "Expected actions came from industry pack defaults (no plan was uploaded)."))

    # B. coverage
    doc.add_heading("B. Plan coverage map", level=2)
    cov = score.get("coverage") or {}
    if not cov.get("present"):
        doc.add_paragraph(cov.get("note") or "No plan uploaded.")
    else:
        counts = cov["counts"]
        doc.add_paragraph(
            f"{counts['followed']} plan items followed, {counts['deviated']} deviated from, {counts['not_reached']} not reached, "
            f"{counts['not_covered']} not covered by this scenario. Not covered is not a failure: it tells the plan owner what the next exercise should test.")
        table(doc, ["Section", "Items", "Followed", "Deviated", "Not reached", "Not covered"],
              [[sec["section"], sec["items"], sec["followed"], sec["deviated"], sec["not_reached"], sec["not_covered"]] for sec in cov["sections"]],
              widths=[1.0, 0.7, 0.8, 0.8, 0.9, 0.9], font_size=8.5)
        deviated = [r for r in cov["rows"] if r["status"] == "deviated"]
        if deviated:
            doc.add_paragraph("Plan items the team deviated from:")
            bullets(doc, [f"Section {r['section']} ({r['item_id']}): {r['label']} (injects {', '.join(r['injects'])})" for r in deviated])
        if cov.get("silent"):
            doc.add_paragraph("Where the plan is silent:")
            bullets(doc, [f"{g['gap_id']}: {g['topic']} ({'exercised' if g['status'] == 'silent_exercised' else 'not exercised in this scenario'})"
                          for g in cov["silent"]])

    # C. gap register
    doc.add_heading("C. Gap register", level=2)
    gaps = score.get("gaps", [])
    if gaps:
        table(doc, ["Id", "Type", "Inject", "Finding", "Citation"],
              [[g["id"], TYPE_LABEL.get(g["label"], g["label"]), g.get("inject_id") or "", g["finding"], g["citation"]] for g in gaps],
              widths=[0.55, 0.65, 0.5, 2.6, 2.6], font_size=7.5)
    else:
        doc.add_paragraph("None.")

    # D. evidence
    doc.add_heading("D. Evidence page", level=2)
    approval = pack.get("approval") or {}
    seed = pack.get("seed") or {}
    demo = score.get("demo") or {}
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
        ("Responses", f"{demo.get('label')}: {_rel(demo.get('responses'))}" if demo else "recorded by the host during the exercise"),
        ("Attendance", "attendance_signin.xlsx and signoff_sheet.docx from the same build"),
        ("Generator", f"Tabletop GM ttx {__version__}; deterministic scoring, rubric in section E"),
    ])
    docs = (pack.get("org_plan") or {}).get("source_documents") or []
    if docs:
        table(doc, ["Id", "Document", "Version", "File"], [[d.get("id"), d.get("title"), d.get("version"), d.get("filename")] for d in docs], font_size=8.5)
        doc.add_paragraph("Every plan statement in this report is a verbatim quote that the validator confirmed exists in the source document.")
    else:
        doc.add_paragraph("Documents exercised: none uploaded.")
    reqs = pack.get("exercise_requirements") or []
    if reqs:
        doc.add_paragraph("Requirements this exercise supports:")
        table(doc, ["Requirement", "Citation", "Tier", "Source"], [[r.get("name"), r.get("citation"), r.get("tier"), r.get("source_url")] for r in reqs], font_size=7.5)
    doc.add_paragraph("Notification deadlines and verification status:")
    table(doc, ["Clock", "Citation", "Tier", "Checked", "Source"],
          [[k["clock_id"], k.get("citation"), k.get("tier"), str(k.get("verified_date")), k.get("source_url")] for k in score["clocks"]], font_size=7.5)
    if researched:
        doc.add_paragraph("Unverified (researched tier): " + ", ".join(k["clock_id"] for k in researched) + ".")
    doc.add_paragraph("Exposure data behind the scenario:")
    rows = []
    for part in ("entry", "pivot", "target"):
        node = seed.get(part) or {}
        rows.append([part, node.get("asset"), node.get("finding_id") or node.get("assumption") or "", node.get("cve") or "", node.get("rule")])
    table(doc, ["Step", "Asset", "Finding or assumption", "CVE", "Selection rule"], rows, font_size=8)
    kv(doc, [("Data source", seed.get("source")), ("Path source", seed.get("path_source"))])
    if seed.get("assumptions"):
        bullets(doc, [f"{a['id']}: {a['text']}" for a in seed["assumptions"]])

    # E. rubric
    doc.add_heading("E. Scoring rubric", level=2)
    table(doc, ["Dimension", "3", "2", "1"],
          [[score["dimension_labels"][d], rub[3], rub[2], rub[1]] for d, rub in ((d, {int(k): v for k, v in score["rubric"][d].items()}) for d in score["rubric"])],
          font_size=8)
