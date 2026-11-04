---
name: scoring_aar
description: The deterministic scoring rubric, gap labels, plan coverage map, and AAR structure, and how to write the AAR headline and summary from the score without adding any number. Use after the exercise, with ttx score and ttx aar.
---

# Scoring and the after-action report

## Score and report in one step

```
ttx report
```

`ttx report` finds the approved exercise and the newest filled tracker for it, scores it, and writes `out/report/` in one step:

- `score.json`
- `after_action_report.docx`
- `executive_summary.pptx`
- `executive_summary.docx`

`/tabletop-report` walks the host through it. `ttx score` and `ttx aar` remain for scripting. Same tracker, same score, every time. The engine scores each recorded decision 1 to 3 on five dimensions. A dimension that does not apply is null and is left out of the totals.

| Dimension | 3 | 2 | 1 |
|---|---|---|---|
| Right owner | the named owner or an accepted delegate decided | another defined role decided | no owner recorded, or an undefined role |
| Timely | within the plan's commitment; at the clock inject, every clock met with an owner | within twice the commitment; regulatory clocks met but an internal standard or an owner missed | slower than twice; a regulatory clock missed or unplanned |
| Escalation and notification | every expected party notified | at least half | fewer than half |
| Documented | documented, decision written down | partly | not documented |
| Followed the plan | every expected action and the plan step followed | at least half, or the step in part | fewer than half, or the step not followed |

Inject rows left blank count as "not reached". A plan-silent inject is not scored on "followed the plan"; it produces a plan gap instead.

## Gap labels

- **Plan gap**: the plan is silent or unclear. Cite the gap id or the section. Fix the document.
- **People gap**: the plan says X at section Y and the team did Z. Cite the verbatim quote. Fix with training or role clarity.
- **Technical gap**: an open finding on the exercised path. Cite the finding ID. Fix the system and rerun the path next quarter.

Every gap carries an owner role and a due date (people 30 days, plan 60, technical 45, KEV technical 14, from the exercise date).

## Plan coverage map

Every org plan item is followed, deviated from, not reached, or not covered by this scenario; every recorded gap topic is silent and exercised or silent and not exercised. "Not covered" is not a failure; it tells the plan owner what the next exercise should test.

## The after-action report

About two pages, then an appendix. The body has the headline and result, lessons learned, one row per decision, the notification deadlines, and the action plan, where gaps that share a fix are grouped into one row with the gap ids it closes. The appendix holds the scores by dimension, the plan coverage map, the gap register with citations, the evidence page, and the rubric. Finding IDs appear only in the appendix.

## Demo responses

`ttx report --demo` scores the invented answers in `samples/demo_responses/responses.yaml` against the approved exercise (or the built-in sample) and writes to `out/report_demo/`. Every output is marked as demo data. Never present demo results as findings.

## The executive summary

Senior management gets seven slides and a one-page memo built from the same content.

- **Bottom line:** a plain-language sentence giving the readiness rating, the score, and the biggest exposure.
- **Overall readiness:** Strong (85% and up), Adequate (70 to 84%), or Needs work (below 70%).
- **Area status:** five areas, each Good (2.5 and up on the 3-point scale), Mixed (2.0 to 2.4), or Weak (below 2.0).
- **Regulatory exposure:** missed or unplanned notices.
- **Top three risks.**
- **Lessons learned:** up to three things that worked (areas rated Good, decisions handled in full, every deadline met) and up to five to improve (unready notices, plan silences, decisions made by the wrong role, parties not told, slow escalation, skipped steps, the open attack path). Each is built from the score, never written freehand.
- **Top five fixes,** with owner and due date.
- **Decisions needed from leadership.**

It never shows finding IDs or rubric detail; the after-action report has those.

## A better headline

The engine writes a default headline. To write a better one, create `out/narrative.json`:

```json
{
  "headline": "One sentence leadership will remember.",
  "summary": ["Two or three short paragraphs."]
}
```

and pass `ttx report --narrative out/narrative.json`. The headline replaces the default in the after-action report and in both executive summary files. The build rejects any number in the narrative that does not appear in the score or the pack.

## How to write the narrative

- Lead with the line leadership remembers: the one clock that was missed or unowned, or the one decision nobody could make. Use the clock's name and the hours from `score.json`.
- Then what went well, in one sentence, from the highest dimension average.
- Then the three fixes that matter most, by owner. Pick from the gaps; do not invent new ones.
- Name roles, not people. The exercise tests plans and roles, never individuals.
- If any clock is researched tier, say so in the summary.
- No em dashes; plain sentences.

## Explaining the result to the person

Give the headline, the score, the clock line, and the top three gaps with owners. Offer the coverage map's "not covered" list as the scope for the next exercise.
