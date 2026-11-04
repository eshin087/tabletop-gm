# Live GM mode: build addendum for Claude Code

Add a third way to run an exercise: Claude facilitates the tabletop live in the Claude Code chat. No deck, no projector slides, no paper tracker. The chat itself is on the projector. The host types what the room decides; the engine logs it; the same score and AAR pipeline runs at the end. This is additive: nothing in the existing prep, build, score, or AAR paths changes behavior.

Credit: design adapted from Steven's live-mode brief (Nov 3), fitted to the existing `ttx` CLI instead of an MCP server.

## How it runs, end to end

1. Prep is unchanged: intake, ingest, seed, clocks, outline, narrate, review, `ttx approve`. The approved `out/exercise_pack.json` is the only input live mode needs. `ttx build` is optional beforehand (no deck is used).
2. The host opens a **fresh Claude Code session** in the repo on the day of the exercise and says "Run the exercise live" (or invokes `/tabletop` and picks live). A fresh session matters: the prep chat contains spoilers, the live chat must never.
3. Claude follows `skills/facilitate/SKILL.md`: ready check, ground rules, then one inject at a time. The host reads the room's answers aloud or the room reads the projector; either way the host types the room's decision into chat.
4. After each decision Claude runs `ttx log add ...`. At `END`, Claude shows the log for the host to correct, exports it, scores it, and builds the record set: filled tracker, AAR with a decision timeline appendix, sign-off sheet, and a chat recap.

## 1. New CLI: `ttx log` (deterministic, append-only)

New module `ttx/decision_log.py`, wired into `ttx/cli.py`. The log is `out/live/decision_log.json`. Every mutation appends; nothing is destroyed. Wall-clock timestamps come from the engine, never from the model.

| Command | Does |
|---|---|
| `ttx log start --pack out/exercise_pack.json --out out/live` | Creates the log: pack path, the pack's approval hash, session start timestamp, facilitator name (`--by`). Refuses an unapproved pack or a pack whose approval hash does not verify. Refuses to start if a log already exists unless `--resume`. |
| `ttx log add --inject <id> --decision "..." --by <role_id> [--notified a,b] [--actions e1,e2] [--plan-step yes\|partial\|no\|plan_unclear\|n/a] [--documented yes\|partial\|no] [--scenario-minutes N] [--note "..."]` | Appends one entry with an auto wall-clock timestamp and computed `discussion_minutes` (delta since the previous entry or session start). Refuses an inject id not in the pack. Refuses a role id not in the pack roles (use `--by other --note` for outsiders). Unknown action ids are refused. Echoes the saved entry. |
| `ttx log add --inject <id> --unplanned --decision "..." --by <role_id>` | Logs an action the plan did not anticipate. Stored with `unplanned: true`. Unplanned entries appear in the AAR timeline but are never scored; the rubric only covers planned decision points, which keeps scoring deterministic. |
| `ttx log note --text "..."` | Freeform timestamped facilitator note (pauses, attendance changes, tech issues). |
| `ttx log mark --inject <id> --event presented\|skipped` | Timestamps when an inject went on screen or was skipped. Skips show in the AAR. |
| `ttx log edit --entry N --field value ...` | Correction during the review step. The original entry is kept with `superseded_by`; the edit records who asked (`--by`) and when. The export uses the latest version. |
| `ttx log show` | The log as a readable table. |
| `ttx log clocks --owner <clock_id>=<role_id> --planned-hours <clock_id>=N ...` | Records the team's clock answers (owner named, planned notify hours), same meaning as the tracker's Clocks sheet. |
| `ttx log export --out out/live` | Writes `decisions.csv` and `decisions_clocks.csv` in exactly the shapes in `schemas/tracker_columns.yaml`, plus `decision_log.json` stays as the audit original. `ttx score` already accepts a CSV decision log plus a `_clocks.csv`; do not change `score_engine`. |

Keep `ttx log` pure stdlib plus what the repo already depends on. No new dependencies, no network. Note in SECURITY.md that live mode adds no outbound calls.

## 2. New skill: `skills/facilitate/SKILL.md`

Claude's conduct during the live session. The chat is projected, so every audience-facing message must be short, readable from the back of a room, and free of file paths, command output, and meta talk. Run `ttx` commands with minimal narration.

Session flow:
1. Silently bootstrap (as the entry skill does), load `out/exercise_pack.json`, run `ttx log start`. If the pack is missing or unapproved, say so in one line and stop.
2. Ready card: organization, scenario family, severity, duration, the roles expected in the room, ground rules (no blame; we test the plan, not the people; the facts are fixed), and the host commands `PAUSE`, `RESUME`, `SKIP`, `END`. Then: "Type START when the room is ready."
3. One inject at a time, in pack order: scenario time, the inject text (reworded to flow from what the room just decided, facts unchanged), then the decision it forces. Run `ttx log mark --event presented` when it goes up.
4. After the host types the room's answer: if the owner is unclear, ask exactly one question, "Who owns this decision?" Then `ttx log add` and move on. At most two follow-up questions per inject, drawn from the pack's probing questions.
5. Stakeholder pressure: Claude may speak short labeled lines as roles the pack defines (for example **CEO:** "Do we pay or not? The board wants an answer by noon."). Labels always, one or two lines, only to force the decision the inject already poses.
6. When the clocks become relevant, ask the pack's clock questions and record with `ttx log clocks`.
7. On `END` or after the last inject: tell the room the exercise is over and the hot wash begins. Show `ttx log show` output. The host corrects anything misheard with `ttx log edit`. Then export, score, build, recap (section 3).

Claude may: reword inject narration; ask up to two follow-ups; speak labeled stakeholder lines; add pressure when the room stalls; acknowledge an off-script answer, log it as unplanned, and steer back to the spine.

Claude may not: introduce a system, finding, deadline, or number that is not in the pack or a `ttx` result; skip or reorder injects on its own (`SKIP` is the host's command); reveal an upcoming inject, an expected action, or what a good answer was, until the recap; change scenario facts because the room asked "what if" (answer: "That's not known to you yet," and continue); editorialize on the quality of an answer mid-exercise.

Off-script handling:

| The room says | Claude does |
|---|---|
| Something matching a planned decision | Logs it, continues |
| Something reasonable the plan did not anticipate | Logs it with `--unplanned`, one follow-up at most, continues the spine |
| "What if X?" | "That's not known to you yet." Continues. |
| Asks for information the pack does not contain | "You'd have to find that out. Who would you ask?" Logs who they would ask as a note. |

## 3. After the session: the record set

1. `ttx log export --out out/live`
2. `ttx score --pack out/exercise_pack.json --tracker out/live/decisions.csv --out out/live/score.json`
3. `ttx build out/exercise_pack.json --out out/live/build` if not built in prep, then `ttx aar --pack out/exercise_pack.json --score out/live/score.json --log out/live/decision_log.json --out out/live/build/after_action_report.docx`
4. In chat, the recap per `skills/scoring_aar/SKILL.md`: the headline line, scores, gaps, clock results, and only now what the expected good answers were.

`ttx aar` gains one optional flag: `--log` appends **Appendix: decision timeline**, every logged entry (planned and unplanned, plus skips and notes) with wall-clock time, scenario time, decision, owner, and score where scored, and a line naming the facilitator, session start and end, and the log file as the audit original. No other AAR change.

## 4. Entry skill and docs edits

- `SKILL.md` step 8 becomes "Run" with two options: **A. In the room with the deck** (current text) and **B. Live in this chat**: tell the person to start a fresh session on exercise day and follow `skills/facilitate/SKILL.md`; warn in one line that running it in the prep chat would expose spoilers.
- Add `skills/facilitate/SKILL.md` to the sub-skills table.
- `.claude/skills/tabletop/SKILL.md` description: add "or facilitate the exercise live in chat".
- README: one short "Run it live in chat" paragraph under how-to-run, and the known limitation: live mode relies on the host typing the room's decisions; voice capture is roadmap.
- `docs/CLI.md`: document `ttx log` and the live pipeline.
- `docs/DECISIONS.md`: record this addendum's decisions (fresh session for spoilers, unplanned entries unscored, CSV export reuses the tracker shapes, no MCP server).

## 5. Tests (pytest, all offline)

- `log start` refuses an unapproved pack and a tampered approval hash
- `log add` refuses an unknown inject id, an unknown role id, an unknown action id
- `log edit` preserves the original entry and the export uses the edited version
- `log export` columns exactly match `schemas/tracker_columns.yaml` (extend the existing column-sync test)
- a scripted log of good decisions scores higher than a scripted log of poor ones on every dimension, and the poor log misses a clock (add the two scripted logs under `samples/`)
- `ttx score` on the same exported log twice is byte-identical
- `aar --log` includes unplanned entries and skipped injects in the timeline

## 6. Order of work and the deadline rule

Build order: `decision_log.py` and `ttx log` with tests, then `log export` and the scripted-team tests, then `aar --log`, then `skills/facilitate/SKILL.md`, then the docs edits. Commit after each.

Deadline rule: the PR must be opened by 11am PT Wednesday regardless. If pytest is not fully green on this addendum by 9:00am PT, revert the README and CLI.md mentions, leave the code on a branch, open the PR without it, and merge it to main afterward. Never let this feature block the submission.
