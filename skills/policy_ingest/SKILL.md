---
name: policy_ingest
description: Fill org_plan.json from the organization's uploaded IR plan, BCP/DR plan, playbooks, procedures, and communication templates, with a verbatim quote and locator for every item, so the exercise tests the organization's own written plan.
---

# Policy ingest

Auditors and regulators ask whether the organization followed its own written plan. This skill turns the uploaded documents into `org_plan.json`: a list of plan items, each backed by a quote the validator confirms exists in the source. Scenario design, scoring, and the AAR's plan coverage map all read this file.

## Inputs

```
ttx ingest-plan uploads/<files> --out out/plan_text.json
```

`plan_text.json` lists each document (`D1`, `D2`...) with its sections: `id`, `heading`, `number` (for example `4.1`), `page` (PDF only), and `text`. Read it section by section. Do not summarize the whole document first; work item by item.

## Output shape

Follow `samples/org_plan_sample.json` exactly. Top level: `present: true`, `source_documents` (id, filename, title, version), `items`, `gaps`.

Each item:

| Field | Rule |
|---|---|
| `id` | P1, P2, ... unique |
| `category` | one of `role`, `decision_authority`, `severity_level`, `escalation_step`, `notification_procedure`, `containment_procedure`, `recovery_objective`, `playbook_step`, `comms_template`, `other` |
| `label` | a short name in the plan's words |
| `value` | your one-line restatement (used in checklists) |
| `quote` | verbatim text from the document, one or two sentences, at least 8 characters |
| `document` | the document id (`D1`) |
| `document_title` | short title used in citations, for example "IR Plan" |
| `section` | the section number from `plan_text.json` |
| `phase` | for actionable items: `detection`, `escalation`, `containment`, `recovery`, or `notification` |
| `timing_minutes` | when the quote states a time limit, in minutes (15 minutes is 15; 24 hours is 1440) |
| `role_id` | for `role` items: a snake_case id; reuse pack role ids where the role matches (`incident_commander`, `cio`, `general_counsel`, `privacy_officer`, `communications`, `ceo`) |
| `internal_deadline_hours`, `applies_to_clock` | when the plan sets its own notification deadline for a regulatory clock, the hours and the clock id from `ttx clocks` |
| `rto_hours`, `rpo_minutes`, `system` | for recovery objectives |

## What to extract (in this order)

1. Roles and decision authorities: who declares, who sets severity, who can shut down a production system, who talks to regulators, law enforcement, and the insurer, who approves public statements, who decides on a ransom.
2. Severity scheme and thresholds.
3. Escalation path and every timing commitment ("within 15 minutes", "within 1 hour").
4. Notification procedures and internal deadlines, especially any stricter than the regulatory clocks.
5. Containment and recovery procedures, RTO and RPO per system, restore order, backup validation.
6. Playbook steps for the scenario family in play.
7. Communication templates and their approval chains.

## Quote rules

- Copy the words exactly. The validator ignores case, extra whitespace, and curly versus straight quotes, nothing else. Do not fix typos, do not join sentences from different paragraphs, do not use ellipses.
- One claim per item. If a sentence carries two authorities, make two items with the same quote.
- Never put a claim in `value` that the quote does not support.

## Gaps

Record explicitly what the plan is silent on, as `gaps` entries with `id` (G1...), `topic`, and `note`. Always check: ransom payment authority and attacker communication, EMS diversion or business shutdown authority, each applicable regulatory clock (compare with `ttx clocks`), staff social media, third-party or vendor incidents, and out-of-hours escalation. At least one inject will pressure a gap.

## Validate

```
ttx validate org-plan out/org_plan.json --plan-text out/plan_text.json
```

Fix every error. A quote that is "not found" means you paraphrased; go back to the section text.

## Guardrails

- Documents stay in `uploads/`. Never copy plan text into committed files. Only the synthetic `samples/sample_ir_plan.md` ships in the repo.
- Scanned PDFs with no text layer fail extraction (OCR is roadmap). Say so and continue with pack defaults, labeled.
- If a document exceeds the size limit, ask the person for the IR plan and the ransomware playbook first; those carry most of the exercise.
