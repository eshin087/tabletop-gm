"""Decision tracker (openpyxl), designed for the host to fill in live.

Sheets:
  Host tracker         one block per inject: plain questions with dropdowns
                       (who decided, how fast, Yes/No per expected action and
                       per notification, plan followed, written down) and two
                       optional typed notes
  Notification clocks  one row per clock: who owns it and when they will notify
  Lists, About         hidden: dropdown values, role ids, and the approval hash
                       so `ttx report` can match the tracker to its exercise

Column A of the visible sheets holds hidden machine keys (I3|action|I3-P6) so
score_engine reads the answers exactly. The CSV decision-log format
(score_engine.DECISION_COLUMNS) is unchanged and still accepted by ttx score.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

# dropdown text -> engine value
YES_NO = ["Yes", "No"]
SPEED = {
    "Immediately": 5, "Within 15 minutes": 15, "Within 30 minutes": 30, "Within 1 hour": 60,
    "Within 4 hours": 240, "Same day": 720, "Next day or later": 1440, "Not stated": None,
}
DISCUSSION = ["5", "10", "15", "20", "30", "45"]
PLAN_STEP = {"Yes": "yes", "Partly": "partial", "No": "no", "The plan was unclear": "plan_unclear", "Not applicable": "n/a"}
DOCUMENTED = {"Yes": "yes", "Partly": "partial", "No": "no"}
CLOCK_TIMING = {
    "Within 24 hours": 24, "Within 72 hours": 72, "Within 7 days": 168, "Within 15 days": 360,
    "Within 30 days": 720, "Within 45 days": 1080, "Within 60 days": 1440, "Within 90 days": 2160,
    "Not planned": None,
}

HOST_SHEET = "Host tracker"
CLOCK_SHEET = "Notification clocks"
NAVY = "1F2A44"
PHASE_FILL = {"detection": "2E6FB7", "escalation": "8A4FB5", "containment": "C25B12", "recovery": "2E8B57", "notification": "B02418"}
INPUT = PatternFill("solid", fgColor="FFF7D6")
HINT_FONT = Font(italic=True, color="5F6B7A", size=10)
LABEL_FONT = Font(size=11)
WRAP = Alignment(wrap_text=True, vertical="center")
THIN = Side(style="thin", color="D0D5DD")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _lists_sheet(wb, pack: dict) -> dict[str, str]:
    ws = wb.create_sheet("Lists")
    columns = {
        "A": ("role_name", [r.get("name") or r["id"] for r in pack.get("roles", [])]),
        "B": ("role_id", [r["id"] for r in pack.get("roles", [])]),
        "C": ("yes_no", YES_NO),
        "D": ("speed", list(SPEED)),
        "E": ("discussion", DISCUSSION),
        "F": ("plan_step", list(PLAN_STEP)),
        "G": ("documented", list(DOCUMENTED)),
        "H": ("clock_timing", list(CLOCK_TIMING)),
    }
    refs = {}
    for col, (name, values) in columns.items():
        ws[f"{col}1"] = name
        for i, v in enumerate(values, start=2):
            ws[f"{col}{i}"] = v
        refs[name] = f"=Lists!${col}$2:${col}${max(len(values) + 1, 2)}"
    ws.sheet_state = "hidden"
    return refs


def _about_sheet(wb, pack: dict, draft: bool) -> None:
    ws = wb.create_sheet("About")
    approval = pack.get("approval") or {}
    for k, v in (("title", pack.get("title")), ("outline_hash", approval.get("outline_hash")),
                 ("approved_by", approval.get("approved_by")), ("draft", "yes" if draft else "no"),
                 ("tracker_version", "2")):
        ws.append([k, v])
    ws.sheet_state = "hidden"


def _dropdown(ws, ref: str, cell: str, allow_other: bool = False) -> None:
    dv = DataValidation(type="list", formula1=ref, allow_blank=True)
    if allow_other:
        dv.showErrorMessage = False  # the host may type another value, for example "Within 50 days"
    ws.add_data_validation(dv)
    dv.add(cell)


def _role_name(pack: dict, role_id: str | None) -> str:
    for r in pack.get("roles", []):
        if r["id"] == role_id:
            return r.get("name") or role_id
    return role_id or ""


def _party_name(pack: dict, party_id: str) -> str:
    for p in pack.get("notify_parties", []):
        if p["id"] == party_id:
            return p.get("name") or party_id
    return party_id


def _short_source(action: dict, pack: dict) -> str:
    src = action.get("source") or ""
    if src.startswith("org_plan:"):
        iid = src.split(":", 1)[1]
        item = next((i for i in (pack.get("org_plan") or {}).get("items", []) if i["id"] == iid), None)
        if item:
            return f"{item.get('document_title') or 'Plan'} {item.get('section') or ''}".strip()
    if src.startswith("pack_default"):
        return "Industry default"
    return ""


def build_tracker(pack: dict, path: str | Path, draft: bool = False) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = HOST_SHEET
    refs = _lists_sheet(wb, pack)
    _about_sheet(wb, pack, draft)

    ws.column_dimensions["A"].hidden = True
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 58
    ws.column_dimensions["C"].width = 30
    ws.column_dimensions["D"].width = 52
    ws.sheet_view.showGridLines = False

    ws.append([None, ("DRAFT  |  " if draft else "") + "Decision tracker", None, None])
    ws["B1"].font = Font(bold=True, size=16, color=NAVY)
    ws.append([None, pack.get("title")])
    ws["B2"].font = Font(size=11, color="5F6B7A")
    ws.append([None, "Fill the yellow cells as each inject finishes. Pick from the dropdowns; only the two note rows are typed. "
                     "Save the file when you are done, then run /tabletop-report in Claude Code."])
    ws.merge_cells("B3:D3")
    ws["B3"].alignment = WRAP
    ws.row_dimensions[3].height = 32
    ws.append([])

    yes_cells: list[str] = []
    for inj in pack.get("injects", []):
        iid = inj["id"]
        r = ws.max_row + 1
        ws.cell(row=r, column=1, value=f"{iid}|header")
        banner = f"INJECT {inj['order']}  |  Slide {inj.get('slide_number')}  |  {inj.get('time_marker')}  |  {str(inj.get('phase')).title()}:  {inj.get('title')}"
        ws.cell(row=r, column=2, value=banner)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        fill = PatternFill("solid", fgColor=PHASE_FILL.get(inj.get("phase"), NAVY))
        for c in range(2, 5):
            ws.cell(row=r, column=c).fill = fill
        ws.cell(row=r, column=2).font = Font(bold=True, color="FFFFFF", size=12)
        ws.row_dimensions[r].height = 22

        commitment = inj.get("plan_commitment_minutes")
        proc = inj.get("procedure_tested") or {}
        rows: list[tuple[str, str, str | None, str, bool]] = [
            ("decided_by", "Who made the call?", refs["role_name"], f"Expected: {_role_name(pack, inj.get('decision_owner_role'))}", False),
            ("speed", "How fast did they say they would act?", refs["speed"],
             f"The plan commits to {int(commitment)} minutes" if commitment and commitment < 1440 else "", False),
            ("discussion", "Minutes the room spent on this inject", refs["discussion"], f"Budget: {inj.get('time_budget_minutes')} minutes", True),
        ]
        for a in inj.get("expected_actions") or []:
            rows.append((f"action|{a['id']}", f"Did they: {a['text']}", refs["yes_no"], _short_source(a, pack), False))
        for n in inj.get("expected_notifications") or []:
            rows.append((f"notify|{n}", f"Did they tell: {_party_name(pack, n)}", refs["yes_no"], "", False))
        if proc.get("type") == "plan_silent":
            rows.append(("plan_step", "Did they follow the plan?", refs["plan_step"], "The plan is silent here: pick Not applicable", False))
        else:
            rows.append(("plan_step", "Did they follow the plan?", refs["plan_step"], proc.get("label") or "", False))
        rows.append(("documented", "Was the decision written down?", refs["documented"], "", False))
        rows.append(("decision", "What did they decide? (optional, type a short note)", None, "", False))
        rows.append(("notes", "Anything else worth noting? (optional)", None, "", False))

        for key, label, ref, hint, allow_other in rows:
            r = ws.max_row + 1
            ws.cell(row=r, column=1, value=f"{iid}|{key}")
            lc = ws.cell(row=r, column=2, value=label)
            lc.font = LABEL_FONT
            lc.alignment = WRAP
            ic = ws.cell(row=r, column=3)
            ic.fill = INPUT
            ic.border = BOX
            ic.alignment = WRAP
            hc = ws.cell(row=r, column=4, value=hint)
            hc.font = HINT_FONT
            hc.alignment = WRAP
            if ref:
                _dropdown(ws, ref, f"C{r}", allow_other=allow_other)
            if ref == refs["yes_no"]:
                yes_cells.append(f"C{r}")
            if key in {"decision", "notes"}:
                # typed notes get the answer and hint columns together, and room for two or three lines
                ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)
                ws.row_dimensions[r].height = 48
        ws.append([])

    # conditional-format fills need start and end colors set for Excel to paint them
    green = PatternFill(start_color="CDEFD6", end_color="CDEFD6", fill_type="solid")
    red = PatternFill(start_color="F8D7D4", end_color="F8D7D4", fill_type="solid")
    last = ws.max_row
    ws.conditional_formatting.add(f"C5:C{last}", CellIsRule(operator="equal", formula=['"Yes"'], fill=green))
    ws.conditional_formatting.add(f"C5:C{last}", CellIsRule(operator="equal", formula=['"No"'], fill=red))
    ws.freeze_panes = "B5"
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "1:3"

    _clock_sheet(wb, pack, refs, draft)
    wb.move_sheet("Lists", offset=10)
    wb.move_sheet("About", offset=10)
    wb.active = 0
    path = Path(path)
    wb.save(path)
    return path


def _deadline_words(c: dict) -> str:
    if c.get("deadline_hours") is not None:
        h = c["deadline_hours"]
        words = f"{int(h // 24)} days" if h >= 72 and h % 24 == 0 else f"{h:g} hours"
    elif c.get("deadline_business_days") is not None:
        words = f"{c['deadline_business_days']} business days"
    else:
        return "No fixed deadline"
    if c.get("after_clock"):
        words += " after the related notice"
    return words


def _clock_sheet(wb, pack: dict, refs: dict, draft: bool) -> None:
    ws = wb.create_sheet(CLOCK_SHEET, 1)
    ws.sheet_view.showGridLines = False
    widths = {"A": 4, "B": 52, "C": 24, "D": 30, "E": 26, "F": 34}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    ws.column_dimensions["A"].hidden = True
    start = next((j for j in pack.get("injects", []) if (j.get("flags") or {}).get("starts_clock")), None)
    ws.append([None, ("DRAFT  |  " if draft else "") + "Notification clocks"])
    ws["B1"].font = Font(bold=True, size=16, color=NAVY)
    ws.append([None, f"Fill this at inject {start['order']} ({start.get('title')}), when the clocks start. "
                     "For each notice, pick who owns it and when the team plans to send it." if start else
                     "Pick who owns each notice and when the team plans to send it."])
    ws.merge_cells("B2:F2")
    ws["B2"].alignment = WRAP
    ws.row_dimensions[2].height = 32
    ws.append([])
    headers = [None, "Notice", "Deadline", "Who owns it?", "When will they send it?", "Check"]
    ws.append(headers)
    for c in range(2, 7):
        cell = ws.cell(row=4, column=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.alignment = WRAP
    for c in pack.get("clocks", []):
        r = ws.max_row + 1
        ws.cell(row=r, column=1, value=c["id"])
        ws.cell(row=r, column=2, value=c.get("name")).alignment = WRAP
        ws.cell(row=r, column=3, value=_deadline_words(c)).alignment = WRAP
        for col in (2, 3, 4, 5):
            ws.cell(row=r, column=col).alignment = WRAP
        for col in (4, 5):
            cell = ws.cell(row=r, column=col)
            cell.fill = INPUT
            cell.border = BOX
        _dropdown(ws, refs["role_name"], f"D{r}")
        _dropdown(ws, refs["clock_timing"], f"E{r}", allow_other=True)
        note = ws.cell(row=r, column=6, value="Verify the deadline before relying on it" if c.get("tier") != "verified" else "")
        note.font = HINT_FONT
        note.alignment = WRAP
        ws.row_dimensions[r].height = 30
    ws.freeze_panes = "B5"
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0


# --------------------------------------------------------------------------- #
# Reading and filling (shared by score_engine and the sample run)
# --------------------------------------------------------------------------- #

def is_host_tracker(wb) -> bool:
    return HOST_SHEET in wb.sheetnames


def _num_from_text(value) -> float | None:
    """Accept dropdown text, plain numbers, or typed values like '50 days' or '6 hours'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    for word, mult in (("day", 24.0), ("hour", 1.0)):
        if word in text:
            digits = "".join(ch if (ch.isdigit() or ch == ".") else " " for ch in text).split()
            if digits:
                return float(digits[0]) * mult
    try:
        return float(text)
    except ValueError:
        return None


def read_host_tracker(wb) -> tuple[dict, dict, dict]:
    """Return (decisions, clocks, meta) in score_engine's row shape."""
    lists = wb["Lists"]
    name_to_id = {}
    for name, rid in lists.iter_rows(min_row=2, max_col=2, values_only=True):
        if name and rid:
            name_to_id[str(name)] = str(rid)
    meta = {}
    if "About" in wb.sheetnames:
        for k, v in wb["About"].iter_rows(max_col=2, values_only=True):
            if k:
                meta[str(k)] = v
    decisions: dict[str, dict] = {}
    actions: dict[str, list[str]] = {}
    notified: dict[str, list[str]] = {}
    answered: set[str] = set()
    for row in wb[HOST_SHEET].iter_rows(values_only=True):
        key = row[0] if row else None
        if not key or "|" not in str(key):
            continue
        iid, field, *rest = str(key).split("|")
        value = row[2] if len(row) > 2 else None
        if isinstance(value, str):
            value = value.strip() or None
        d = decisions.setdefault(iid, {"inject_id": iid})
        if value in (None, "") or field == "header":
            continue
        answered.add(iid)
        if field == "decided_by":
            d["decided_by_role"] = name_to_id.get(str(value), str(value))
        elif field == "speed":
            d["scenario_minutes"] = SPEED.get(str(value), _num_from_text(value)) if str(value) in SPEED else _num_from_text(value)
        elif field == "discussion":
            d["discussion_minutes"] = _num_from_text(value)
        elif field == "action" and str(value).lower() == "yes":
            actions.setdefault(iid, []).append(rest[0])
        elif field == "notify" and str(value).lower() == "yes":
            notified.setdefault(iid, []).append(rest[0])
        elif field == "plan_step":
            d["plan_step_followed"] = PLAN_STEP.get(str(value), str(value).lower())
        elif field == "documented":
            d["documented"] = DOCUMENTED.get(str(value), str(value).lower())
        elif field in {"decision", "notes"}:
            d[field] = str(value)
    out = {}
    for iid, d in decisions.items():
        if iid not in answered:
            continue
        d["actions_completed"] = ", ".join(actions.get(iid, []))
        d["notified"] = ", ".join(notified.get(iid, []))
        d["_answered"] = True
        out[iid] = d
    clocks: dict[str, dict] = {}
    if CLOCK_SHEET in wb.sheetnames:
        for row in wb[CLOCK_SHEET].iter_rows(min_row=5, values_only=True):
            cid = row[0] if row else None
            if not cid:
                continue
            owner, timing = (row[3] if len(row) > 3 else None), (row[4] if len(row) > 4 else None)
            hours = CLOCK_TIMING.get(str(timing), _num_from_text(timing)) if timing not in (None, "") else None
            clocks[str(cid)] = {"clock_id": str(cid), "owner_role": name_to_id.get(str(owner), owner) if owner else None,
                                "planned_notify_hours": hours}
    return out, clocks, meta


def fill_host_tracker(path: str | Path, pack: dict, decisions: dict[str, dict], clocks: dict[str, tuple[str, str]],
                      out_path: str | Path | None = None) -> Path:
    """Fill a built tracker the way a host would, using dropdown text.

    decisions: {inject_id: {"decided_by": role_id, "speed": SPEED key, "discussion": "10", "actions": [ids],
                "notified": [party ids], "plan_step": PLAN_STEP key, "documented": DOCUMENTED key,
                "decision": text, "notes": text}}
    clocks: {clock_id: (role_id, CLOCK_TIMING key)}
    """
    wb = load_workbook(path)
    ws = wb[HOST_SHEET]
    for row in ws.iter_rows(min_row=1):
        key = row[0].value
        if not key or "|" not in str(key):
            continue
        iid, field, *rest = str(key).split("|")
        d = decisions.get(iid)
        if not d:
            continue
        cell = row[2]
        if field == "decided_by" and d.get("decided_by"):
            cell.value = _role_name(pack, d["decided_by"])
        elif field in {"speed", "discussion", "plan_step", "documented", "decision", "notes"} and d.get(field) is not None:
            cell.value = d[field]
        elif field == "action":
            cell.value = "Yes" if rest[0] in d.get("actions", []) else "No"
        elif field == "notify":
            cell.value = "Yes" if rest[0] in d.get("notified", []) else "No"
    wc = wb[CLOCK_SHEET]
    for row in wc.iter_rows(min_row=5):
        cid = row[0].value
        if cid in clocks:
            owner, timing = clocks[cid]
            row[3].value = _role_name(pack, owner)
            row[4].value = timing
    target = Path(out_path or path)
    wb.save(target)
    return target
