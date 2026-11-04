# Tabletop GM

Tabletop GM builds a cybersecurity tabletop exercise in an afternoon. It tailors the exercise three ways:

- **Industry and regulators.** An industry pack supplies the notification clocks and exercise requirements, each with a source link.
- **Real exposure.** The attack path comes from Tenable data, an uploaded scan export, or a synthetic sample estate.
- **Your own written plans.** Your uploaded IR plan, playbooks, and procedures become the procedures each inject tests.

It ships as a Claude Code skill (`/tabletop`) on top of a deterministic Python engine (`ttx`). The engine computes everything that must be correct: the attack path, the deadlines, the citations, the validation, the documents, and the scores. Claude does the judgment work: the interview, reading your plans, writing and reviewing the story, and explaining the results. Every document can be rebuilt from the approved exercise pack with no API key and no model call.

## What it does

1. **Intake.** One chat message covers organization, industry, jurisdictions, data types, regulated status, severity 1 to 4, audience, and duration (60, 90, or 180 minutes).
2. **Policy ingest (optional).** `ttx ingest-plan` extracts your plans with section anchors. Claude fills `org_plan.json`, where every item carries a verbatim quote, and the validator rejects any quote it cannot find in the source.
3. **Data pull.** `ttx seed` picks the entry, pivot, and crown jewel from your exposure data and records the rule that fired for each.
   - The entry is an exploitable internet-facing finding, KEV first, then highest VPR.
   - The pivot is an identity-tier or high-criticality server.
   - The crown jewel is the highest-criticality asset holding your data types.
   - With no data, the scenario is generic and every assumption is labeled.
4. **Clocks.** `ttx clocks` returns the notification deadlines that apply to you, each with its source URL, checked date, and tier.
5. **Outline.** `ttx outline` writes a complete, valid skeleton of the exercise. Each inject cites a finding or a labeled assumption and names the plan procedure it tests. Claude refines the narrative, then reviews it adversarially.
6. **Approval gate.** A human approves the outline with `ttx approve`. Nothing builds before that, and any later edit breaks the approval hash.
7. **Build.** `ttx build` produces the deck, facilitator guide, handout, decision tracker, attendance sheet, and sign-off sheet.
8. **Score and report.** `ttx score` scores the tracker against your plan, or the pack defaults when you uploaded none. `ttx aar` writes the after-action report with gap labels, the plan coverage map, and an evidence page.

Industry packs shipped (`ttx packs`):

| Pack | Clocks | Exercise requirements |
|---|---|---|
| healthcare | 7 | 2 |
| banking (banks and credit unions) | 8 | 2 |
| insurance (incl. NYDFS Part 500) | 4 | 2 |
| public_sector (state, local, tribal, K-12) | 8 | 1 |
| higher_education | 3 | 2 |
| saas_technology | 10 | 1 |
| retail_ecommerce | 2 | 1 |
| manufacturing_ot | 5 | 3 |
| energy_utilities | 9 | 3 |
| federal_contractors | 6 | 2 |
| `clocks_common.yaml` (GDPR, UK GDPR, SEC 8-K, CIRCIA, Visa, state breach laws) | 56 | n/a |

Every clock is at the researched tier: drafted from a primary source with a citation, not yet human-verified. See Known limitations. The `pack_research` skill drafts a pack for any other industry from `skills/industry_packs/_template/`.

## Prerequisites

- Python 3.11 or newer.
- git.
- No API keys for the engine, the sample run, or any document build.
- Claude Code for the guided `/tabletop` workflow (intake, policy ingest, narrative, review, AAR narrative).
- Optional: read-only Tenable Vulnerability Management or Tenable One API keys in `.env` for live mode.
- Optional: the `pytenable` package. Live mode falls back to the standard library when it is not installed.

Dependencies are pure Python: python-pptx, python-docx, openpyxl, pyyaml, pypdf, and jinja2. There is no Docker, Node, database, cloud service, or account.

## How to run

All commands run from the repository root.

Install:

```bash
git clone https://github.com/eshin087/tabletop-gm.git
cd tabletop-gm
python -m venv .venv
```

Activate the venv. On macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

Then:

```bash
pip install -e ".[dev]"
pytest -q
```

### Rebuild the sample exercise (no keys, no network, no model)

The repository ships an approved sample exercise for Valley Regional Health System, a fictional 1,200-employee health system. These commands rebuild every document from it and re-score its synthetic completed tracker:

```bash
ttx validate exercise-pack samples/exercise_pack_sample.json
ttx build samples/exercise_pack_sample.json --out out/sample_build
ttx score --pack samples/exercise_pack_sample.json --tracker samples/outputs/decision_tracker_completed.xlsx --out out/score.json
ttx aar --pack samples/exercise_pack_sample.json --score out/score.json --out out/sample_build/after_action_report.docx
```

### Run the full pipeline step by step

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

After the exercise, fill `out/build/decision_tracker.xlsx` (Decisions and Clocks sheets), then:

```bash
ttx score --pack out/exercise_pack.json --tracker out/build/decision_tracker.xlsx --out out/score.json
ttx aar --pack out/exercise_pack.json --score out/score.json --out out/build/after_action_report.docx
```

Regenerate everything in `samples/outputs/` (this overwrites the committed sample files):

```bash
python samples/make_sample_run.py
```

### Use your own data

- **Export mode.** Put a findings export in `uploads/` (CSV, JSON, or .nessus), plus an optional asset export. Set `environment.mode: export` and `environment.estate_file` in your intake, or pass `--mode export --estate uploads/findings.csv --assets uploads/assets.csv`. Column mapping is config-driven with fuzzy header matching (`schemas/export_columns.yaml`). It was built from the Tenable field names recorded in the build spec and is tested against Tenable-shaped CSV and JSON. Add aliases there for another scanner.
- **Live mode.** Copy `.env.example` to `.env`, fill in `TENABLE_ACCESS_KEY` and `TENABLE_SECRET_KEY`, and run `ttx seed --mode tenable --save`. `--save` writes the pulled estate to `uploads/` so the same run can be replayed in export mode.
- **KEV cross-check.** Add `--kev-check` to `ttx seed` to compare the scanner's KEV flags with the public CISA catalog. Use `--kev-file` to compare against a local copy instead.
- **Your plans.** Put them in `uploads/` and run `ttx ingest-plan uploads/<files> --out out/plan_text.json`. In Claude Code, the `policy_ingest` skill fills `out/org_plan.json` from them.

### Guided workflow in Claude Code

Open Claude Code in the repository root and type `/tabletop`. The project skill in `.claude/skills/tabletop/` loads the entry skill `SKILL.md`. That skill interviews you, runs the commands above, writes the narrative with the ten sub-skills in `skills/`, and stops at the approval gate for your sign-off.

## Outputs

`ttx build` writes these from the approved `exercise_pack.json` only:

| File | For | Contents |
|---|---|---|
| `deck.pptx` | The room | Title, ground rules, objectives, roles, setup, one slide per inject, hot wash, next steps. Inject slides are numbered to match the guide. Host lines are in the speaker notes. No spoilers. |
| `facilitator_guide.docx` | Facilitator | Timing table, then per inject: host lines, the decision and its owner, a "what the plan says" box with the verbatim quote, good answers, where teams fail, expected-action checklists, hints, probing questions, and the source finding. Ends with every clock and its source. |
| `participant_handout.docx` | Everyone | Roles, ground rules, a contact-list template, and note space. No inject content. |
| `decision_tracker.xlsx` | Host, live | One row per inject (decision, role, minutes, notified, actions, plan step, documented) and a Clocks sheet (owner, planned hours). `ttx score` reads it. |
| `attendance_signin.xlsx`, `signoff_sheet.docx` | Audit evidence | Sign-in and roles-present sheets. The sign-off covers scope, approval record, documents exercised, requirements supported, clocks, and an attestation. |
| `after_action_report.docx` (from `ttx aar`) | Leadership, auditors | Headline, scores by dimension and decision, and regulatory exposure: each clock met or missed by hours, plus the plan's own standards. Plan, people, and technical gaps with citation, fix, owner, and due date. Plan coverage map, decision log, and an evidence page with hashes. |

`samples/outputs/` holds one complete synthetic run: the documents above plus `seed.json`, `clocks.json`, `exercise_pack.json`, a synthetic completed tracker, and `score.json`. The sample scores 82.8%. Its regulatory clock line is the HIPAA media notice, missed by 60 hours. The California health department report had no owner. The sample report lists 2 plan gaps, 11 people gaps, and 3 technical gaps.

## Known limitations

- **No clock is human-verified yet.** All 118 clocks were drafted by Claude from primary sources on 2026-11-03, but no human has checked them. Every output that uses them carries a "verify before exercise" banner, and the AAR evidence page lists them as unverified. A few clocks whose source could not be fetched say so in their notes. To promote a clock, set `tier: verified`, `verifier`, and `verified_date` after opening its source.
- **Deadline arithmetic is simplified.**
  - Business-day deadlines skip weekends but not public holidays.
  - Calendar-month deadlines are stored as 720 hours.
  - "Concurrent with" and "prior to" agency notices are modeled with the parent deadline. Only explicit "within N days after notice" clocks are chained.
- **Some thresholds are approximate.** Per-state resident thresholds use the intake's total affected estimate. Clock applicability depends on the intake's regulated flags being right.
- **Live Tenable mode is untested in CI.** It uses read-only export endpoints and the field names recorded in the build spec. Automated tests cannot reach the network, so live mode is not exercised there.
- **Attack paths are inferred.** Tenable One attack path ingestion is not wired to the API, so live runs report `path_source: inferred` unless the estate file carries `attack_paths`.
- **Crown-jewel matching is heuristic.** When assets carry no data tags, it falls back to hostname and software patterns, and the seed records which rule fired.
- **Some inputs are not supported.** Scanned PDFs (OCR) are not supported. The .nessus parser reads only the basic fields.
- **The CLI never calls a model.** `ttx outline` writes template prose that is valid and buildable but generic. The tailored narrative comes from Claude in the `/tabletop` workflow.
- **Scoring is only as good as the tracker.** It is deterministic given the tracker, but timeliness uses the minutes the host records.
- **Samples are synthetic.** Valley Regional, its estate, its IR plan, and its completed tracker are invented. CVE identifiers are real public identifiers, used so the KEV logic means something. IP addresses use documentation ranges.
- **Only one host workflow ships.** The browser host console (`host.html`) and `ttx host` are not shipped. Run the exercise from the facilitator guide and the tracker; see Roadmap.

## Roadmap

- `host.html`: a self-contained host console for a second laptop, with click-based decision capture, a timer, optional browser speech-to-text, and tracker export.
- `ttx host`: a standard-library local server with an AI co-host that follows `skills/host_copilot/SKILL.md`.
- Human verification of the healthcare and banking clocks first, then the rest.
- More packs through `pack_research`, plus community contributions.
- Tenable One attack path API ingestion and a Qualys/Rapid7 column map.
- Voice host, Slack and Teams rooms, an adaptive attacker, and quarterly reruns on unfixed paths.
- An MCP wrapper over the `ttx` commands.

See `SECURITY.md` for every outbound call and `docs/DECISIONS.md` for build decisions. MIT licensed.
