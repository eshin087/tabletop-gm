---
name: scoring_aar
description: The deterministic scoring rubric, gap labels, plan coverage map, and AAR structure, and how to write the AAR headline and summary from the score without adding any number. Use after the exercise, with ttx score and ttx aar.
---

# Scoring and the after-action report

## Score

```
ttx score --pack out/exercise_pack.json --tracker out/build/decision_tracker.xlsx --out out/score.json
```

Same tracker, same score, every time. The engine scores each recorded decision 1 to 3 on five dimensions. A dimension that does not apply is null and is left out of the totals.

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

## Build the report

```
ttx aar --pack out/exercise_pack.json --score out/score.json --out out/build/after_action_report.docx
```

The engine writes a default headline. To write a better one, create `out/narrative.json`:

```json
{
  "headline": "One sentence leadership will remember.",
  "summary": ["Two or three short paragraphs."]
}
```

and pass `--narrative out/narrative.json`. The build rejects any number in the narrative that does not appear in the score or the pack.

## How to write the narrative

- Lead with the line leadership remembers: the one clock that was missed or unowned, or the one decision nobody could make. Use the clock's name and the hours from `score.json`.
- Then what went well, in one sentence, from the highest dimension average.
- Then the three fixes that matter most, by owner. Pick from the gaps; do not invent new ones.
- Name roles, not people. The exercise tests plans and roles, never individuals.
- If any clock is researched tier, say so in the summary.
- No em dashes; plain sentences.

## Explaining the result to the person

Give the headline, the score, the clock line, and the top three gaps with owners. Offer the coverage map's "not covered" list as the scope for the next exercise.
