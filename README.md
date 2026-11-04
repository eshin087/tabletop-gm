# Tabletop GM

Tabletop GM builds a cybersecurity tabletop exercise in an afternoon. It tailors the exercise three ways:

- **Industry and regulators.** An industry pack supplies the notification clocks and exercise requirements, each with a source link.
- **Real exposure.** The attack path comes from Tenable data, an uploaded scan export, or a synthetic sample estate.
- **Your own written plans.** Your uploaded IR plan, playbooks, and procedures become the procedures each inject tests.

It ships as a Claude Code skill (`/tabletop`) on top of a deterministic Python engine (`ttx`). The engine computes everything that must be correct: the attack path, the deadlines, the citations, the validation, the documents, and the scores. Claude does the judgment work: the interview, reading your plans, writing and reviewing the story, and explaining the results. Every document can be rebuilt from the approved exercise pack with no API key and no model call.

**Try it:** download the ZIP, double-click the launcher for your computer, and choose 1. See [Quick start](#quick-start).

## What it does

1. **Intake.** A quick-start interview: a few screens of clickable choices, with typing only for the organization's name and its US states. It covers industry, length (30, 60, or 90 minutes), severity 1 to 4, the data you hold, and regulated status. Anything not asked uses a default you can change on the summary screen.
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
8. **Score and report.** After the exercise, `/tabletop-report` (or `ttx report`) finds the filled tracker, scores it against your plan or the pack defaults, and writes everything in one step:
   - the after-action report, with gap labels, the plan coverage map, and an evidence page
   - an executive summary for senior management, as seven slides and a one-page memo, including lessons learned

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

- **To see the sample exercise:** nothing. The launcher sets everything up.
- **Python 3.11 or newer.** The Windows launcher offers to install it for you. On macOS it offers Homebrew if you have it, or opens the download page.
- **Internet on the first run only,** to download the document libraries. After that, everything except the guided workflow runs offline.
- **To build an exercise for your own organization:** Claude Code (terminal, desktop app, or IDE) and a Claude account. The launcher tells you how to install it if it's missing.
- **Optional:** read-only Tenable Vulnerability Management or Tenable One API keys, for live exposure data.

There is no git, Docker, Node, database, or cloud service to set up. The dependencies are pure Python: python-pptx, python-docx, openpyxl, pyyaml, pypdf, and jinja2.

## How to run

### Quick start

1. **Download.** On this GitHub page, click **Code**, then **Download ZIP**, and unzip it anywhere. Or clone it with git.
2. **Double-click the launcher for your computer:**
   - Windows: `start-windows.bat`
   - macOS: `start-mac.command`. The first time, macOS may warn about an unidentified developer: right-click the file, choose **Open**, then **Open** again.
   - Linux: run `./start-linux.sh` in a terminal.
3. **Pick from the menu:**
   - **1. See a finished sample exercise.** About 10 seconds, no account. It builds the complete Valley Regional exercise (a fictional health system) and opens the folder. Start with `START_HERE.txt`.
   - **2. Build an exercise for my organization.** This opens Claude Code in the folder and starts the `/tabletop` interview.
   - **3. Run an exercise live in chat.** Claude facilitates in the chat. With nothing built yet, it runs the sample exercise. See [Run it live in chat](#run-it-live-in-chat).

The first run takes a minute or two. The launcher creates a private `.venv` folder inside the download and installs into it, so nothing else on your computer changes. Later runs go straight to the menu.

### What happens in option 2

`/tabletop` opens with four choices: build a new exercise, score one you've run, run one live in chat, or see the sample.

**Building takes a few minutes, mostly clicks:**

1. Type the organization's name.
2. Click through industry, length (30, 60, or 90 minutes), severity, and whether it's publicly traded.
3. Type the US states it operates in.
4. Tick the data it holds and the regulated statuses that apply.
5. Pick the exposure data source.
6. Review a summary screen with sensible defaults for everything else.

You can drop your IR plan, playbooks, or scan exports into the `uploads/` folder, and Claude offers to use them.

Claude then shows the outline as a table: each inject, the decision it forces, who owns it, and which of your procedures it tests. Click **Approve**, **Change an inject**, **Make it easier**, or **Make it harder**. Nothing is built until you approve. The documents land in `out/build/` and the folder opens.

**After the exercise:**

1. Save the filled tracker into the `uploads` folder, or drag it into the chat.
2. Type `/tabletop-report`.

It scores the tracker and writes the after-action report and the executive summary into `out/report/`.

**For a pitch or a practice run:** type `/tabletop-report` and choose demo responses, or run `ttx report --demo --open`. It scores the invented answers in `samples/demo_responses/` against your approved exercise (or the built-in sample) and writes the same reports into `out/report_demo/`, marked as demo data on every page.

The project pre-approves only Tabletop GM's own commands (`.claude/settings.json`), so Claude Code doesn't ask permission at every step. Claude Code shows these rules in its trust prompt the first time you open the folder.

If you already use Claude Code, you can skip the launcher. Open the downloaded folder in Claude Code and type `/tabletop`; it installs what it needs on its own.

### Run it live in chat

Skip the deck and let Claude run the room.

1. Open a new chat in the folder, type `/tabletop`, and choose **Run an exercise live**. Use a new chat, not the one where you built the exercise, because that one holds the answers.
2. Pick your exercise, or the built-in sample if you just want to try it.
3. Put the chat on the projector. Claude shows one inject at a time. You type what the room decides.
4. Type `END` when you're done. Claude shows the log for corrections, then writes the scored after-action report and executive summary into `out/live/`.

You can type `PAUSE`, `RESUME`, or `SKIP` at any point.

### Command line

Everything the launcher and Claude do is a plain `ttx` command, and every document can be rebuilt with no model call. See [docs/CLI.md](docs/CLI.md) for manual install, the full pipeline step by step, export and live Tenable modes, and every command.

## Outputs

`ttx build` writes these from the approved `exercise_pack.json` only:

| File | For | Contents |
|---|---|---|
| `deck.pptx` | The room | Title, ground rules, objectives, roles, setup, one slide per inject, hot wash, next steps. Inject slides are numbered to match the guide. Host lines are in the speaker notes. No spoilers. |
| `facilitator_guide.docx` | Facilitator | Timing table, then per inject: host lines, the decision and its owner, a "what the plan says" box with the verbatim quote, good answers, where teams fail, expected-action checklists, hints, probing questions, and the source finding. Ends with every clock and its source. |
| `participant_handout.docx` | Everyone | Roles, ground rules, a contact-list template, and note space. No inject content. |
| `decision_tracker.xlsx` | Host, live | One color-coded block per inject with plain questions and dropdowns: who made the call, how fast, Yes/No for each expected action and notification, plan followed, written down. Only the two optional note rows are typed. A Notification clocks sheet records who owns each notice and when they'll send it. `ttx report` reads it. |
| `attendance_signin.xlsx`, `signoff_sheet.docx` | Audit evidence | Sign-in and roles-present sheets. The sign-off covers scope, approval record, documents exercised, requirements supported, clocks, and an attestation. |
| `after_action_report.docx` (from `ttx report`) | Security team, auditors | About two pages: headline and readiness rating, lessons learned (what worked, what to improve), one row per decision, each notification deadline met or missed, and an action plan with owners and due dates. The appendix holds the scores by dimension, the plan coverage map, every gap with its citation, and an evidence page with hashes. |
| `executive_summary.pptx`, `executive_summary.docx` (from `ttx report`) | Senior management | Seven slides and a one-page memo: a plain-language bottom line, an overall readiness rating (Strong, Adequate, Needs work), regulatory exposure, the top three risks, lessons learned, the top five fixes with owners and dates, and the decisions needed from leadership. No finding IDs or rubric detail. |
| `out/live/decision_log.json`, `decisions.csv`, `decisions_clocks.csv` (from `ttx log`) | Live mode | The append-only decision log of a chat-facilitated session (the audit original) and its export in the tracker's column shapes, which `ttx score` reads unchanged. |

Option 1 in the launcher (or `ttx demo`) rebuilds the same sample into `out/demo/` with a `START_HERE.txt` guide. `samples/outputs/` holds one complete synthetic run: the documents above plus `seed.json`, `clocks.json`, `exercise_pack.json`, a synthetic completed tracker, and `score.json`. The sample rates Adequate at 82.8%. Its regulatory clock line is the HIPAA media notice, planned 30 days late. The California health department report had no owner. The sample report lists 2 plan gaps, 11 people gaps, and 3 technical gaps.

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
- **Pre-approved commands depend on Claude Code's trust prompt.** Claude Code applies the project's allow rules only after you accept the trust prompt for the folder. The Windows rule's backslash path has not been confirmed in a live session; if Claude Code still asks, choose "don't ask again" once.
- **Executive ratings use fixed thresholds.** Strong is 85% and up, Adequate is 70 to 84%, and Needs work is below 70%. Tune them to your organization's appetite in `ttx/build/exec_summary.py`.
- **Launchers were tested on Windows only.** The Windows launcher was run from a fresh copy. The macOS and Linux launchers are plain shell scripts but have not been run on a Mac or a Linux desktop yet. macOS Gatekeeper asks for a right-click Open the first time.
- **Live mode relies on the host typing.** When Claude facilitates in chat, the record is only as complete as what the host types in; voice capture of the room is roadmap. Timestamps and discussion minutes are measured from when each decision is typed.
- **No host console ships.** The browser host console (`host.html`) and `ttx host` are not shipped. Run the exercise from the facilitator guide and the tracker, or live in chat; see Roadmap.

## Roadmap

- `host.html`: a self-contained host console for a second laptop, with click-based decision capture, a timer, optional browser speech-to-text, and tracker export.
- `ttx host`: a standard-library local server with an AI co-host that follows `skills/host_copilot/SKILL.md`.
- Human verification of the healthcare and banking clocks first, then the rest.
- More packs through `pack_research`, plus community contributions.
- Tenable One attack path API ingestion and a Qualys/Rapid7 column map.
- Voice host, Slack and Teams rooms, an adaptive attacker, and quarterly reruns on unfixed paths.
- An MCP wrapper over the `ttx` commands.

See `SECURITY.md` for every outbound call and `docs/DECISIONS.md` for build decisions. MIT licensed.
