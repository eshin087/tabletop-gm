---
name: severity_levels
description: The four tabletop severity levels, what each tests, and what each scenario must include. Use when choosing the severity at intake and when checking an outline honors it.
---

# Severity levels

| Level | Example | What it tests | Must include (`severity_musts`) |
|---|---|---|---|
| 1 Contained | One compromised mailbox, no data loss | Detection and the escalation path | `alert`, `escalation`: an alert and an escalation call |
| 2 Serious | Business email compromise with a fraudulent wire, or limited data exposure | Legal, finance, the notification threshold | `money_or_data_decision`, `legal`: a money or data decision, legal pulled in |
| 3 Major | Ransomware across systems, operations down | Containment, recovery, executive decisions | `outage`, `ransom_note`, `restore_order`: an outage, a ransom note, a restore-order decision |
| 4 Crisis | Ransomware plus extortion, a key vendor down, media and regulator calling | Everything at once, communication under pressure | `three_pressures`, `public_statement`: three simultaneous pressures and a public statement |

Phases follow NIST SP 800-61r3: detection, escalation, containment, recovery, notification. Inject count is fixed by duration: 5 for 60 minutes, 7 for 90, 10 for 180.

## Choosing a level

- First exercise for this team, or a technical-only room: level 1 or 2.
- The organization has never exercised its ransomware playbook, or the auditor asked about it: level 3.
- An executive room that has exercised before, or a board-level rehearsal: level 4.
- If the seed's target holds regulated data (PHI, PCI, PFI, CUI) the notification phase will be real at any level; level 1 still starts the clock if data is touched.
- When in doubt, one level lower. A room that is overwhelmed learns less than a room that is stretched.

## Honoring the level

`ttx outline` sets `severity_musts` for the level and writes slots that include them. When you refine the story, keep each must visible in at least one inject's `what_happens` or host lines. The validator warns when a must is not set; `outline_review` checks the prose actually delivers it.

Level 4 needs three pressures at the same time (for example the outage, a vendor saying their service is also down, and a reporter calling). Put them in one inject, not three in a row.
