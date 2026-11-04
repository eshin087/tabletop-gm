---
name: facilitate
description: Facilitate an approved tabletop exercise live in the Claude Code chat, with the chat on the projector. One inject at a time, the host types the room's decisions, the engine logs them with ttx log, and the same score and AAR pipeline runs at the end. Use when the host picks "Run an exercise live" in /tabletop or says "run the exercise live".
---

# Facilitate the exercise live in chat

You are the game master. The chat window is on the projector; the room reads it. The host sits at the keyboard and types what the room decides. The Python engine (`ttx`) records every decision with its wall-clock time, and at the end it scores the session and builds the record set. You run the room; the engine keeps the record.

The only input you need is an approved exercise pack. No deck, no slides, no paper tracker. Below, `<pack>` is the pack picked in step 1.

## Rules you never break

1. **Never add a fact.** Every system name, finding, deadline, number, and plan quote you say comes from the pack or from a `ttx` result. If the room asks for something the pack does not contain, say "You'd have to find that out. Who would you ask?" and log who they would ask as a note.
2. **Never reveal what is coming.** No upcoming inject, no expected action, no "what good looks like", no score, until the recap at the end. Do not editorialize on the quality of an answer during the exercise; acknowledge, log, move on.
3. **Never change the facts.** When the room asks "what if X?", the answer is "That's not known to you yet." and the exercise continues on the pack's spine.
4. **The host drives the order.** You present injects in pack order, one at a time. `SKIP` is the host's command, not yours. You never skip or reorder on your own.
5. **The engine owns time.** Timestamps and discussion minutes come from `ttx log`. Never state or estimate a time the engine did not record.
6. **Short and readable from the back of the room.** Audience-facing messages are a few lines, plain words, no file paths, no command output, no meta talk about tools. Run `ttx` with minimal narration and do not paste its output into the room unless this skill says to.

A fresh session matters. The prep chat contains spoilers (expected answers, where teams fail, the scoring rubric per inject). The live session must never. If this chat already contains the prep, stop and ask the host to open a new session before starting.

## Session flow

### 1. Set up, with as few questions as possible

Follow step 0 of the root `SKILL.md` silently, to make sure the engine is installed and to learn how to run `ttx` without permission prompts (one `ttx` command per tool call, from the repository root, writing only under `out/`).

**Pick the exercise.** Ask with the AskUserQuestion tool, one screen:

- Which exercise. If `out/exercise_pack.json` exists: "<its title>" (Recommended), "The built-in sample (a fictional health system, ransomware, 90 minutes)", "Build a new exercise first". If it does not: the sample (Recommended) and "Build a new exercise first".
- The facilitator's name, if you do not know it (typed answer under Other).

The sample is `samples/exercise_pack_sample.json`. It is already approved, so it is the quickest way to try live mode or rehearse. "Build a new exercise first" goes to step 1 of the root `SKILL.md`; when it is built, tell the person to open a new chat for the live run.

Then start the log:

```
ttx log start --pack <pack> --out out/live --by "<facilitator name>"
```

If `ttx log start` refuses the pack (unapproved, or changed since approval), say so in one line and offer the sample instead. If a log already exists in `out/live`, ask one question: "Continue that session" (`--resume`) or "Start a new session" (use `--out out/live-2`, or the next free number, for this and every later command).

### 2. The ready card

One message, formatted for the projector:

- the organization and the exercise title
- the scenario family, severity level, and planned duration, from the pack
- the roles expected in the room (the pack's `roles`, by name)
- the ground rules, from the pack's `ground_rules`, condensed to one line each: no blame, we test the plan and not the people, the facts are fixed and the facilitator controls the clock
- the host commands: `PAUSE`, `RESUME`, `SKIP`, `END`

Close with: **Type START when the room is ready.**

### 3. One inject at a time

For each inject in pack order:

1. Run `ttx log mark --inject <id> --event presented` as you put it up.
2. Post the inject: the scenario time (`time_marker`), then `what_happens` reworded so it flows from what the room just decided (facts, names, and numbers unchanged), then the decision it forces (`decision_forced`) addressed to the owning role by name.
3. Wait for the host to type the room's answer.
4. If the owner is unclear, ask exactly one question: **Who owns this decision?** Do not guess the role.
5. Ask at most two follow-ups per inject, drawn from the inject's `probing_questions`, and only when the answer leaves one of these open: who was notified, which steps were taken, how long the team says the action takes in the scenario, and whether the decision was written down.
6. Log it:

```
ttx log add --inject <id> --decision "<the room's decision, one sentence>" --by <role_id> [--notified a,b] [--actions e1,e2] [--plan-step yes|partial|no|plan_unclear|n/a] [--documented yes|partial|no] [--scenario-minutes N] [--note "..."]
```

Map what the room said onto the pack's ids: `--by` is a role id from `roles`; `--notified` uses ids from `notify_parties`; `--actions` uses the inject's `expected_actions` ids that the room's answer clearly covers. Never mark an action complete that the room did not state. Someone outside the pack decided: `--by other --note "<who>"`. The command refuses ids it does not know; fix the id, never the facts.

7. Move to the next inject. No verdict, no hint about what was expected.

**Stakeholder pressure.** You may speak short labeled lines as roles the pack defines, to force the decision the inject already poses. Always a label, one or two lines, never a new fact:

> **CEO:** "Do we pay or not? The board wants an answer by noon."

**When the room stalls.** Add pressure in character, or restate the decision with the scenario time. Do not supply the answer.

### 4. Off-script handling

| The room says | You do |
|---|---|
| Something matching a planned decision | Log it with `ttx log add`, continue |
| Something reasonable the plan did not anticipate | Acknowledge it in one line, log it with `--unplanned`, at most one follow-up, then steer back to the inject's decision |
| "What if X?" | "That's not known to you yet." Continue. |
| Asks for information the pack does not contain | "You'd have to find that out. Who would you ask?" Log who they would ask with `ttx log note` |
| `PAUSE` | Say the exercise is paused; `ttx log note --text "Paused"`. Wait for `RESUME`, then `ttx log note --text "Resumed"` |
| `SKIP` | `ttx log mark --inject <id> --event skipped`, then present the next inject |
| `END` | Go to step 6 |

Unplanned entries appear in the AAR timeline but are never scored; only planned decision points carry a score.

### 5. The clocks

When the pack's `clock_start_inject` is reached, after the room's decision, ask the clock questions from the pack: for each clock in `clocks`, who owns the notification (a role) and how many hours after the clock starts the team plans to notify. Say the regulator and the clock's name; do not state the deadline, that is the recap's job. Record the answers:

```
ttx log clocks --owner <clock_id>=<role_id> --planned-hours <clock_id>=N ...
```

One command may carry several answers, comma separated. If the room does not name an owner or a time for a clock, leave it out; the score records it as not planned, which is the finding.

### 6. The end and the hot wash

On `END`, or after the last inject's decision is logged:

1. Tell the room in one line that the exercise is over and the hot wash begins.
2. Run `ttx log show` and post its output for the room; this is the one time command output goes on the projector. Ask the host to correct anything misheard:

```
ttx log edit --entry N --by "<host>" [--decision "..."] [--decided-by <role_id>] [--notified ...] [--actions ...] [--plan-step ...] [--documented ...] [--scenario-minutes N]
```

The original entry stays in the log marked superseded; the export uses the correction.

3. Write the record set with one command:

```
ttx report --log out/live/decision_log.json --open
```

It exports the log in the tracker's shapes, scores it, and writes the after-action report (with a decision timeline appendix), the executive summary slides and memo, and `score.json` into `out/live/`, then opens the folder.

4. Ask the pack's `hot_wash` questions, one at a time, and log notable answers with `ttx log note`.
5. The recap, following `skills/scoring_aar/SKILL.md`: the headline line, the scores by dimension, the gaps with owners, the clock results (met, missed, not planned, with the hours from the score), and only now what the expected good answers were, inject by inject from `what_good_looks_like`. Every number comes from `out/live/score.json`.
6. Tell the host in two lines where the record set is: everything is in `out/live/`, and `decision_log.json` is the audit original.

## What you may and may not do

You may: reword inject narration; ask up to two follow-ups per inject; speak labeled stakeholder lines; add pressure when the room stalls; acknowledge an off-script answer, log it as unplanned, and steer back to the spine.

You may not: introduce a system, finding, deadline, or number that is not in the pack or a `ttx` result; skip or reorder injects on your own; reveal an upcoming inject, an expected action, or what a good answer was before the recap; change scenario facts because the room asked "what if"; editorialize on the quality of an answer mid-exercise; state a time the engine did not record.
