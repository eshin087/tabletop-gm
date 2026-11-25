# Tabletop GM command reference

For engineers, reviewers, and anyone scripting Tabletop GM. Most people should use the launcher described in the README instead.

## Install by hand

```bash
git clone https://github.com/eshin087/tabletop-gm.git
cd tabletop-gm
```

Create and activate a virtual environment. On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope Process Bypass` first. Then install and run the tests:

```bash
pip install -e ".[dev]"
pytest -q
```

`python scripts/bootstrap.py --setup` does the same install without activating anything and prints the `ttx` path to use.

All commands below run from the repository root.

## The sample in one step

```bash
ttx demo
```

Builds the complete synthetic exercise into `out/demo`, writes `START_HERE.txt`, and opens the folder. Add `--no-open` on a server.

## Rebuild the committed sample (no keys, no network, no model)

```bash
ttx validate exercise-pack samples/exercise_pack_sample.json
ttx build samples/exercise_pack_sample.json --out out/sample_build
ttx score --pack samples/exercise_pack_sample.json --tracker samples/outputs/decision_tracker_completed.xlsx --out out/score.json
ttx aar --pack samples/exercise_pack_sample.json --score out/score.json --out out/sample_build/after_action_report.docx
```

## The full pipeline, step by step

```bash
ttx packs
ttx validate packs
ttx ingest-plan samples/sample_ir_plan.md --out out/plan_text.json
ttx validate org-plan samples/org_plan_sample.json --plan-text out/plan_text.json
ttx seed --intake samples/intake_valley_regional.yaml --out out/seed.json
ttx clocks --intake samples/intake_valley_regional.yaml --out out/clocks.json
ttx outline --intake samples/intake_valley_regional.yaml --seed out/seed.json --clocks out/clocks.json --org-plan samples/org_plan_sample.json --out out/exercise_pack.json
ttx narrate out/exercise_pack.json samples/narrative_overlay_sample.json
```

`ttx narrate` applies the narrative the scenario_design skill writes. It changes narrative fields only and refuses any change to sources, procedures, expected actions, or clocks.

`ttx build` refuses an unapproved outline (exit code 2, "not approved"). Review the outline, approve it, then build:

```bash
ttx approve out/exercise_pack.json --by "Your Name"
ttx build out/exercise_pack.json --out out/build
```

After the exercise, fill `out/build/decision_tracker.xlsx` (the Host tracker and Notification clocks sheets), save it, then:

```bash
ttx report --open
```

`ttx report` finds the approved exercise and the newest filled tracker for it in `uploads/` or `out/`, then writes four files into `out/report/`: `score.json`, `after_action_report.docx`, `executive_summary.pptx`, and `executive_summary.docx`. Pass `--tracker <file>` to name the tracker yourself.

For a pitch or a practice run, `ttx report --demo` scores the synthetic answers in `samples/demo_responses/responses.yaml` against the approved exercise (or the built-in sample exercise when there is none) and writes the same reports, plus `demo_tracker.xlsx`, into `out/report_demo/`. Every output is marked "DEMO: synthetic responses". `--responses <file>` uses your own answers file.

The lower-level steps are still available:

```bash
ttx score --pack out/exercise_pack.json --tracker out/build/decision_tracker.xlsx --out out/score.json
ttx aar --pack out/exercise_pack.json --score out/score.json --out out/build/after_action_report.docx
```

Regenerate everything in `samples/outputs/` (this overwrites the committed sample files):

```bash
python samples/make_sample_run.py
```

## Run the exercise live in chat: `ttx log`

Live mode replaces the deck and the paper tracker with the chat on the projector. Claude follows `skills/facilitate/SKILL.md`; the host types the room's decisions; these commands record them. The log is `out/live/decision_log.json`, append-only: every command adds an entry, corrections keep the original marked `superseded_by`, and timestamps come from the engine.

```bash
ttx log start --pack out/exercise_pack.json --out out/live --by "Facilitator name"
ttx log mark --inject I1 --event presented
ttx log add --inject I1 --decision "Treated it as a suspected SEV1 and called the Incident Commander" --by security_operations --actions I1-P16,I1-d1 --plan-step yes --documented yes --scenario-minutes 10
ttx log add --inject I3 --unplanned --decision "Reset every privileged password" --by cio
ttx log note --text "Ten minute break"
ttx log mark --inject I5 --event skipped
ttx log clocks --owner hipaa_media_notice=communications --planned-hours hipaa_media_notice=1000,hipaa_individual_notice=900
ttx log show
ttx log edit --entry 2 --by "Host" --decision "Treated it as a suspected SEV1; the Incident Commander was reached in 8 minutes"
ttx log export --out out/live
```

Every subcommand takes `--out DIR` (default `out/live`) and reads the pack path recorded at `log start` (override with `--pack`).

| Command | Does |
|---|---|
| `ttx log start --pack --out --by` | Creates the log with the pack's approval hash, the start time, and the facilitator. Refuses an unapproved pack or one changed since approval. Refuses an existing log unless `--resume`. |
| `ttx log add --inject --decision --by [...]` | Appends a decision with the wall-clock time and `discussion_minutes` since the previous entry. Refuses an inject, role, party, or action id the pack does not define; `--by other --note "..."` records someone outside the pack. `--unplanned` marks an action the plan did not anticipate: shown in the AAR, never scored. |
| `ttx log note --text` | Timestamped facilitator note. |
| `ttx log mark --inject --event presented\|skipped` | When an inject went up or was skipped by the host. |
| `ttx log edit --entry N --by WHO [fields]` | Appends a corrected version of a decision entry; the original stays, marked `superseded_by`. Fields: `--decision`, `--decided-by`, `--notified`, `--actions`, `--plan-step`, `--documented`, `--scenario-minutes`, `--discussion-minutes`, `--note`. |
| `ttx log show` | The log as a table. |
| `ttx log clocks --owner id=role --planned-hours id=N` | The team's clock answers, same meaning as the tracker's Clocks sheet. Later answers override earlier ones. |
| `ttx log export --out` | Writes `decisions.csv` and `decisions_clocks.csv` in exactly the tracker's columns (`schemas/tracker_columns.yaml`). `decision_log.json` stays as the audit original. |

Then one command writes the record set. It exports the log, scores it, and writes the AAR with a decision timeline appendix plus the executive summary, all into the log's folder:

```bash
ttx report --log out/live/decision_log.json --open
```

The same steps one at a time: `ttx log export`, then `ttx score --tracker out/live/decisions.csv`, then `ttx aar --log out/live/decision_log.json`.

Two scripted synthetic sessions ship under `samples/live/` (a team that follows the plan and one that does not); `python samples/make_live_logs.py` regenerates them.

## Run the exercise from the host console: `ttx host`

`ttx host` serves two screens in the browser on this computer: the host console at `/`, private to the host, and the room screen at `/room`, for the wall or the projector. It records through the same decision log as `ttx log`, so everything above about the log applies. Ending the exercise in the console runs the same pipeline as `ttx report --log`.

```bash
ttx host
ttx host --pack out/exercise_pack.json --out out/host --by "Facilitator name"
ttx host --pack out/exercise_pack.json --out out/host --resume
ttx host --replay samples/live/poor/decision_log.json
```

| Option | Does |
|---|---|
| `--pack FILE` | The approved exercise pack. Default: `out/exercise_pack.json`, or the built-in sample when that does not exist. An unapproved or changed pack is refused. |
| `--out DIR` | Where the decision log and the reports go. Default `out/host` (`out/host-replay` with `--replay`). An existing log is refused unless `--resume`. |
| `--by NAME` | The facilitator's name, recorded in the log. |
| `--resume` | Continue the session already in `--out`. The log gets a "Session resumed" note. |
| `--replay LOG` | Open a recorded `decision_log.json` read-only and step through it on both screens. The log is copied into `--out`; the original is not written. Scoring works; capture and the AI co-host do not. |
| `--port N` | Port on 127.0.0.1. Default 8765. |
| `--no-ai` | Run from the pack's script even when an API key is present. |
| `--no-open` | Do not open the browser. |

Keys on the host console: Space moves to the next step (present, done reading, they decided), P pushes the room during Discuss, 1 to 9 toggle the expected actions, Ctrl+Enter logs the decision, and T switches light and dark. Add `?theme=dark` or `?theme=light` to the address to pin a theme.

The room screen is read-only and has no controls. Open it from the link in the host console, or at `http://127.0.0.1:8765/room`, and move that window to the projector.

The AI co-host is on when `ANTHROPIC_API_KEY` is in `.env` and the optional package is installed (`pip install -e ".[host]"`). Presenting an inject asks it to write the line for the room, and pushing the room asks it for one stakeholder line; both reach the room screen only after the fact check passes. In the decision box, Enter asks it to suggest what to tick and what to ask next. Four environment variables tune it:

| Variable | Default | Meaning |
|---|---|---|
| `TTX_HOST_MODEL` | `claude-opus-5-5` | The model the co-host calls. `claude-sonnet-5-5` and `claude-haiku-5-5` also work and show a cost estimate. Haiku 5.5 has no server-side fallback, so a declined line falls back to the script. |
| `TTX_HOST_EFFORT` | `low` | Reasoning effort: `low`, `medium`, `high`, `xhigh`, or `max`. Low keeps the room waiting least. |
| `TTX_HOST_FAST` | off | Set to `1` for fast output mode on models that support it, at a higher price. |
| `TTX_HOST_AI` | on | Set to `off` to disable the co-host without removing the key. |

Requests include a server-side fallback, so a request a safety classifier declines by mistake is retried on the model Anthropic recommends. If the co-host still cannot answer, the console shows the pack's script line and says why.

`ttx build PACK --out DIR --only host` writes the standalone `host.html`. It needs no server: open it, run the exercise, export `decision_log.json`, then:

```bash
ttx report --log decision_log.json --pack out/exercise_pack.json
```

## Use your own data

- **Export mode.** Put a findings export in `uploads/` (CSV, JSON, or .nessus), plus an optional asset export. Set `environment.mode: export` and `environment.estate_file` in your intake, or pass `--mode export --estate uploads/findings.csv --assets uploads/assets.csv`. Column mapping is config-driven with fuzzy header matching (`schemas/export_columns.yaml`). It was built from the Tenable field names recorded in the build spec and is tested against Tenable-shaped CSV and JSON. Add aliases there for another scanner.
- **Live mode.** Copy `.env.example` to `.env`, fill in `TENABLE_ACCESS_KEY` and `TENABLE_SECRET_KEY`, and run `ttx seed --intake <intake> --mode tenable --save --out out/seed.json`. `--save` writes the pulled estate to `uploads/` so the same run can be replayed in export mode.
- **KEV cross-check.** Add `--kev-check` to `ttx seed` to compare the scanner's KEV flags with the public CISA catalog. Use `--kev-file` to compare against a local copy instead.
- **Your plans.** Put them in `uploads/` and run `ttx ingest-plan uploads/<files> --out out/plan_text.json`. In Claude Code, the `policy_ingest` skill fills `out/org_plan.json` from them.

## Every command

| Command | Does |
|---|---|
| `ttx demo` | Build the whole sample exercise and open it |
| `ttx report [--log]` | After the exercise: score the tracker, write the AAR and executive summary; `--log` does the same from a live session's decision log |
| `ttx report --demo` | The same reports from synthetic demo responses, for a pitch |
| `ttx packs` | List industry packs and clock counts |
| `ttx flags --industry SLUG --states CA,NV` | Plain-language regulated-status questions for the intake |
| `ttx ingest-plan DOC... --out` | Extract uploaded plans with section anchors |
| `ttx seed --intake --out` | Pick entry, pivot, and target from exposure data |
| `ttx clocks --intake --out` | Applicable notification clocks with sources and tiers |
| `ttx outline ... --out` | Deterministic outline skeleton |
| `ttx narrate PACK OVERLAY` | Apply a narrative overlay (narrative fields only) |
| `ttx validate KIND FILE` | seed, pack, packs, clocks, org-plan, outline, exercise-pack |
| `ttx approve PACK --by NAME` | Human approval gate |
| `ttx build PACK --out [--open]` | Every document from the approved pack, and the standalone `host.html` |
| `ttx score --pack --tracker --out` | Deterministic score from the tracker |
| `ttx aar --pack --score --out [--log]` | After-action report; `--log` adds the live decision timeline appendix |
| `ttx log start\|add\|note\|mark\|edit\|show\|clocks\|export` | Append-only decision log for an exercise run live in chat |
| `ttx host [--pack --out --by --resume --port --no-ai]` | Host console and room screen in the browser: guided steps, click capture, clocks, and a scorecard at the end |
| `ttx host --replay LOG` | Replay a recorded decision log read-only, with no model |

Run `ttx <command> --help` for options.
