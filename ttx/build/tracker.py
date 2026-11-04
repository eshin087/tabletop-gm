"""Decision tracker (openpyxl). The host fills it live, or host.html exports the same columns.

Sheets: Decisions (one row per inject; score_engine reads it), Clocks (owner
and planned notification time per clock), Expected actions, Roles, Parties,
Instructions. Columns match score_engine.DECISION_COLUMNS and CLOCK_COLUMNS.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from ..score_engine import CLOCK_COLUMNS, DECISION_COLUMNS

HEADER_FILL = PatternFill("solid", fgColor="1F2A44")
HEADER_FONT = Font(bold=True, color="FFFFFF")
INPUT_FILL = PatternFill("solid", fgColor="FFFBEA")
WRAP = Alignment(wrap_text=True, vertical="top")


def _header(ws, columns: list[str], widths: dict[str, int]) -> None:
    ws.append(columns)
    for i, col in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=i)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP
        ws.column_dimensions[cell.column_letter].width = widths.get(col, 16)
    ws.freeze_panes = "A2"


def build_tracker(pack: dict, path: str | Path, draft: bool = False) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Decisions"
    widths = {"inject_id": 9, "slide": 7, "time_marker": 9, "phase": 13, "title": 30, "expected_owner": 20, "decision": 45,
              "decided_by_role": 22, "discussion_minutes": 11, "scenario_minutes": 11, "notified": 30, "actions_completed": 30,
              "plan_step_followed": 14, "documented": 12, "notes": 40}
    _header(ws, DECISION_COLUMNS, widths)
    input_cols = {"decision", "decided_by_role", "discussion_minutes", "scenario_minutes", "notified", "actions_completed",
                  "plan_step_followed", "documented", "notes"}
    for inj in pack.get("injects", []):
        ws.append([inj["id"], inj.get("slide_number"), inj.get("time_marker"), inj.get("phase"), inj.get("title"),
                   inj.get("decision_owner_role"), None, None, None, None, None, None, None, None, None])
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.alignment = WRAP
            if DECISION_COLUMNS[cell.column - 1] in input_cols:
                cell.fill = INPUT_FILL
    n = ws.max_row
    role_ids = [r["id"] for r in pack.get("roles", [])]
    roles_formula = f"=Roles!$A$2:$A${len(role_ids) + 1}"
    dv_role = DataValidation(type="list", formula1=roles_formula, allow_blank=True)
    dv_step = DataValidation(type="list", formula1='"yes,partial,no,plan_unclear,n/a"', allow_blank=True)
    dv_doc = DataValidation(type="list", formula1='"yes,partial,no"', allow_blank=True)
    for dv in (dv_role, dv_step, dv_doc):
        ws.add_data_validation(dv)
    col = {c: i + 1 for i, c in enumerate(DECISION_COLUMNS)}
    letter = lambda name: ws.cell(row=1, column=col[name]).column_letter  # noqa: E731
    dv_role.add(f"{letter('decided_by_role')}2:{letter('decided_by_role')}{n}")
    dv_step.add(f"{letter('plan_step_followed')}2:{letter('plan_step_followed')}{n}")
    dv_doc.add(f"{letter('documented')}2:{letter('documented')}{n}")

    # Clocks
    wc = wb.create_sheet("Clocks")
    _header(wc, CLOCK_COLUMNS, {"clock_id": 40, "name": 50, "owner_role": 22, "planned_notify_hours": 14, "internal_deadline_hours": 14, "notes": 50})
    internal = {i.get("applies_to_clock"): i.get("internal_deadline_hours") for i in (pack.get("org_plan") or {}).get("items", []) if i.get("applies_to_clock")}
    for c in pack.get("clocks", []):
        wc.append([c["id"], c.get("name"), c.get("deadline_hours"), c.get("deadline_business_days"), c.get("tier"), None, None,
                   internal.get(c["id"]), "VERIFY BEFORE EXERCISE (researched tier)" if c.get("tier") != "verified" else None])
    for row in wc.iter_rows(min_row=2, max_row=wc.max_row):
        for cell in row:
            cell.alignment = WRAP
        row[5].fill = INPUT_FILL
        row[6].fill = INPUT_FILL
    dv_role2 = DataValidation(type="list", formula1=roles_formula, allow_blank=True)
    wc.add_data_validation(dv_role2)
    dv_role2.add(f"F2:F{max(wc.max_row, 2)}")

    # Expected actions
    wa = wb.create_sheet("Expected actions")
    _header(wa, ["inject_id", "action_id", "action", "source", "expected_notifications"], {"action": 70, "source": 28, "expected_notifications": 40, "action_id": 16})
    for inj in pack.get("injects", []):
        for a in inj.get("expected_actions") or []:
            wa.append([inj["id"], a["id"], a["text"], a.get("source"), ", ".join(inj.get("expected_notifications") or [])])
    for row in wa.iter_rows(min_row=2, max_row=wa.max_row):
        for cell in row:
            cell.alignment = WRAP

    wr = wb.create_sheet("Roles")
    _header(wr, ["role_id", "name", "authority", "source"], {"role_id": 22, "name": 40, "authority": 60, "source": 28})
    for r in pack.get("roles", []):
        wr.append([r["id"], r.get("name"), r.get("authority"), r.get("source")])

    wp = wb.create_sheet("Parties")
    _header(wp, ["party_id", "name"], {"party_id": 26, "name": 60})
    for p in pack.get("notify_parties", []):
        wp.append([p["id"], p.get("name")])

    wi = wb.create_sheet("Instructions")
    lines = [
        "Decision tracker for: " + str(pack.get("title")),
        ("DRAFT: built from an unapproved outline." if draft else "Built from the approved exercise pack."),
        "",
        "Fill the yellow cells. One row per inject on the Decisions sheet.",
        "decision: what the room decided, in a sentence.",
        "decided_by_role: the role id that made the call (list on the Roles sheet).",
        "discussion_minutes: real minutes the room spent on the inject.",
        "scenario_minutes: the in-scenario minutes the team says the action would take (compared with the plan's timing commitments).",
        "notified: party ids the team said it would notify at this inject, comma separated (Parties sheet).",
        "actions_completed: expected action ids that happened, comma separated (Expected actions sheet).",
        "plan_step_followed: yes, partial, no, plan_unclear, or n/a.",
        "documented: yes, partial, or no (was the decision written down the way the plan requires).",
        "Clocks sheet: name the owner role and the planned notification time in hours after the clock starts.",
        "",
        "Then run: ttx score --pack exercise_pack.json --tracker decision_tracker.xlsx --out score.json",
    ]
    for line in lines:
        wi.append([line])
    wi.column_dimensions["A"].width = 120
    wb.move_sheet("Instructions", offset=-(len(wb.sheetnames) - 1))
    wb.active = 1

    path = Path(path)
    wb.save(path)
    return path
