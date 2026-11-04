---
name: scenario_design
description: Turn the deterministic outline skeleton from ttx outline into a timed, escalating tabletop story built on the seed's attack path and the organization's own plan, without adding any fact the engine did not supply.
---

# Scenario design

`ttx outline` already produced a complete, valid `exercise_pack.json`: the inject slots, their phases and timing, the decision owner, the plan procedure each one tests, the expected actions with their sources, the clocks, and plain template prose. Your job is to make the prose read like this organization's incident. You change words, not facts.

## What you may edit

Per inject: `title`, `what_happens`, `recipients`, `decision_forced`, `what_good_looks_like`, `where_teams_fail`, `hints`, `probing_questions`, `host_lines`. At the top level: `scenario.summary`, `objectives`, `ground_rules`, `hot_wash.questions`, `next_steps`.

You may change `decision_owner_role` or `acceptable_owner_roles` only to a role id that exists in `roles`, and only when the org plan names a different owner for that decision. Quote the plan item that justifies it in your message to the person.

## What you must not edit

`id`, `order`, `phase`, `slide_number`, `time_marker`, `minutes_offset`, `source`, `procedure_tested`, `expected_actions`, `expected_notifications`, `plan_commitment_minutes`, `flags`, `seed`, `clocks`, `org_plan`, `roles` entries, `approval`. If one of these looks wrong, say so and rerun the engine with corrected inputs instead of hand-editing.

## Facts you may use in prose

- Asset names, CVEs, VPR, and KEV status from `seed` (entry, pivot, target). Use the asset name the seed gives, never a nicer invented one.
- Role titles from `roles`. System names and timing commitments from `org_plan.items` (quote or paraphrase closely).
- Clock deadlines only as the clock gives them (`deadline_hours`, `deadline_business_days`, `deadline_text`). The validator warns when narrative mentions an hours or days figure that matches no clock.
- Anything the person told you in the intake.

Everything else is either generic texture that adds no fact ("the night shift is thin", "the phones start ringing") or a labeled assumption added to `assumptions` with an id (A5, A6...) and cited by the inject that relies on it.

## Escalation rules (the validator enforces them)

- Each inject raises the stakes or removes an option.
- At least one inject delivers conflicting information (`flags.conflicting_information`).
- At least one forces a business tradeoff (`flags.business_tradeoff`).
- At least one tests a point the plan is silent on (`procedure_tested.type: plan_silent`). Make that inject's pressure land squarely on the silent topic.
- The notification clocks start at a defined inject (`flags.starts_clock`), and the AAR checks them.

## How to write the story

1. Read the seed path aloud to yourself: entry asset and CVE, pivot and technique, target and data. That is the spine. Every inject is a consequence of that path.
2. Read each inject's `procedure_tested`. The inject exists to pressure that procedure. If it tests "IR Plan section 4.1, Security Operations notifies the Incident Commander within 15 minutes", the inject should make the 15 minutes hard to meet (a missed page, an ambiguous alert), not irrelevant.
3. Use the plan's own role names and system names in host lines. The point is that the room hears its own plan being tested.
4. Write for the audience in the intake. Executive rooms get business consequences and fewer system names; technical rooms get the logs.
5. Keep each inject's `what_happens` under 70 words and `decision_forced` to one question.
6. Follow `skills/inject_style/SKILL.md` for voice and `skills/severity_levels/SKILL.md` for what the severity requires.

## Finish

```
ttx validate outline out/exercise_pack.json
```

Zero errors. Warnings about researched clocks are expected; warnings about narrative deadlines are not, so fix them. Then hand off to `skills/outline_review/SKILL.md`.
