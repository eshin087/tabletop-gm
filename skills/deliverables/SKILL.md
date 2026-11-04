---
name: deliverables
description: What each Tabletop GM output contains, slide by slide and section by section, and who it is for. Use when describing the build to the person or checking an output.
---

# Deliverables

`ttx build` produces every document from the approved `exercise_pack.json` only, so nothing contradicts anything else and anyone can rebuild them without a model call. An unapproved or edited pack is refused; `--draft` builds a watermarked DRAFT for review.

## deck.pptx (the room)

The only thing the audience sees. 16:9.

1. Title: organization, scenario family, severity, duration, date, location; a verification note when researched clocks are in play
2. Ground rules
3. Objectives
4. Who is at the table (roles)
5. Scenario setup: organization, data held, where it operates (no attack path)
6 onward. One slide per inject, numbered to match the inject's `slide_number`: time marker and phase, what happens, the decision box, who it reaches. The inject that starts the clocks shows the three tightest clocks. Speaker notes carry the host lines and probing questions.
Last two: hot wash questions, next steps.

The deck never shows expected actions, good answers, failure modes, or finding IDs.

## facilitator_guide.docx (the script)

How to run it, a timing table (inject, time, slide, phase, minutes, owner), then one page per inject: host lines to read aloud, what happens, who receives it, the decision forced and its owner, the plan's timing commitment, a "what the plan says" box (verbatim quote and section, or a red box when the plan is silent), what good looks like, where teams fail, expected actions and notifications as checklists with their ids, hints, probing questions, facilitator notes for conflicting information, tradeoffs, plan-silent points, and clock starts, and the source finding or assumption. Ends with every clock (deadline, tier, checked date, citation, source URL), hot wash questions, and labeled assumptions.

## participant_handout.docx (everyone)

Date and place, objectives, ground rules, the roles table with a "played by" column, a contact-list template for every role and notify party, and note space per update. No spoilers: no inject titles, systems, findings, or answers.

## decision_tracker.xlsx (the host, live)

Built for the host to fill in fast, with dropdowns everywhere except two optional note rows.

`Host tracker` has one color-coded block per inject, headed with its slide number and time. The questions are:

- Who made the call? (role names)
- How fast did they say they would act? (Immediately through Next day or later)
- Minutes the room spent on this inject
- Yes/No for each expected action
- Yes/No for each expected notification
- Did they follow the plan? (Yes, Partly, No, The plan was unclear, Not applicable)
- Was the decision written down?

Each row shows the expected owner or plan reference beside it. Yes turns green and No turns red.

`Notification clocks` has one row per notice, with who owns it and when they will send it (Within 24 hours through Within 90 days; typed values like "Within 50 days" also work).

Hidden sheets hold the dropdown lists and the exercise's approval hash, so `ttx report` can match the tracker to its exercise.

## attendance_signin.xlsx and signoff_sheet.docx (audit evidence)

Sign-in sheet (name, title, role played, department, times, signature) and a roles-present sheet. The sign-off sheet records scope, the approval record, documents exercised, requirements the exercise supports, clocks exercised with tiers, an attestation, and signature lines for the facilitator, the executive sponsor, and the plan owner.

## executive_summary.pptx and executive_summary.docx (senior management)

Built by `ttx report` alongside the after-action report. Seven slides:

1. Title
2. The bottom line: a plain sentence, the overall readiness rating, and five areas marked Good, Mixed, or Weak
3. Regulatory exposure
4. What worries us most: three risks
5. Lessons learned: what worked and what to improve
6. What we are fixing: five actions with owners and due dates
7. Decisions we need from leadership

The memo is the same content on one page, with lessons learned in place of the risks. No finding IDs or rubric detail.

## after_action_report.docx (security team, auditors, regulators)

Built by `ttx report` (or `ttx aar`) from `score.json`. Short by design: about two pages a reader can act on, then an appendix for auditors.

Body:

1. The headline and a one-row result: readiness rating, score, decisions scored, deadlines met, gaps to fix
2. Lessons learned: what worked and what to improve
3. Decision by decision: what the team decided, who decided, the score, and the main issue, one row per inject
4. Notification deadlines: each notice, its limit, what the team planned, met or missed, and the owner
5. Action plan: every gap, grouped so each row is one fix, with type, owner, due date, and the gap ids it closes

Appendix: scores by dimension, the plan coverage map (by section, plus deviations and silent topics), the gap register with every citation, the evidence page (approval record and hash, input hashes, documents, requirements, clocks with verification status, the exposure data behind the scenario), and the scoring rubric. Demo runs (`ttx report --demo`) carry a "DEMO: synthetic responses" box at the top.
