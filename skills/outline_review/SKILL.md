---
name: outline_review
description: Adversarial QA of an exercise outline before the human approval gate. Checks realism, escalation rules, the business tradeoff, plan coverage, severity, and every uncited claim. Use after scenario_design and before ttx approve.
---

# Outline review

Review `out/exercise_pack.json` as a skeptical auditor and a bored executive at the same time. Your job is to find problems, not to admire the outline. Report findings as a list; fix the ones you can within the scenario_design rules; tell the person about the rest before they approve.

## 1. Mechanical checks (run first)

```
ttx validate outline out/exercise_pack.json
```

Any error blocks approval. Any narrative-deadline warning is a finding.

## 2. Uncited claims

For every inject, read `what_happens`, `host_lines`, `what_good_looks_like`, and `hints`. List every system name, number, time, and policy statement. Each must trace to the seed, a clock, an org plan item, the intake, or a labeled assumption. Anything else is a finding: remove it or add an assumption.

## 3. Escalation

- Does each inject raise the stakes or remove an option? Name the one that does not.
- Is the conflicting information credible on both sides?
- Does the business tradeoff have two defensible answers? If one answer is obviously right, it is not a tradeoff.
- Does the plan-silent inject actually pressure the silent topic, or does it drift to something the plan covers?
- Is the notification clock started at a clear moment the room can name?

## 4. Severity

Check `severity_musts` against the prose. Level 3 needs a visible outage, a ransom note, and a restore-order decision; level 4 needs three simultaneous pressures and a public statement.

## 5. Plan coverage

From `org_plan.items`, list the decision authorities and timing commitments no inject tests. If an important one is missing (who declares, who shuts down, who notifies the regulator), say which inject could carry it.

## 6. Realism and audience

- Would someone in this sector believe it? Flag anything that reads like a movie.
- Does the language fit the audience (executive, technical, mixed)?
- Can each inject be discussed in its time budget?

## 7. Safety and hygiene

- No real organization names, no real people, no victim names.
- Defensive framing only: the outline describes what the organization must respond to, never how to carry out an intrusion.
- No secrets, keys, or internal URLs from uploaded documents in the narrative.

## Report

Give the person a short list: blocking findings (must fix before approval), recommended fixes, and notes. Then ask whether they approve the outline.
