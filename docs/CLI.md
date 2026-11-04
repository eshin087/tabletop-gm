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

The lower-level steps are still available:

```bash
ttx score --pack out/exercise_pack.json --tracker out/build/decision_tracker.xlsx --out out/score.json
ttx aar --pack out/exercise_pack.json --score out/score.json --out out/build/after_action_report.docx
```

Regenerate everything in `samples/outputs/` (this overwrites the committed sample files):

```bash
python samples/make_sample_run.py
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
| `ttx report` | After the exercise: score the tracker, write the AAR and executive summary |
| `ttx packs` | List industry packs and clock counts |
| `ttx flags --industry SLUG --states CA,NV` | Plain-language regulated-status questions for the intake |
| `ttx ingest-plan DOC... --out` | Extract uploaded plans with section anchors |
| `ttx seed --intake --out` | Pick entry, pivot, and target from exposure data |
| `ttx clocks --intake --out` | Applicable notification clocks with sources and tiers |
| `ttx outline ... --out` | Deterministic outline skeleton |
| `ttx narrate PACK OVERLAY` | Apply a narrative overlay (narrative fields only) |
| `ttx validate KIND FILE` | seed, pack, packs, clocks, org-plan, outline, exercise-pack |
| `ttx approve PACK --by NAME` | Human approval gate |
| `ttx build PACK --out [--open]` | Every document from the approved pack |
| `ttx score --pack --tracker --out` | Deterministic score from the tracker |
| `ttx aar --pack --score --out` | After-action report |

Run `ttx <command> --help` for options.
