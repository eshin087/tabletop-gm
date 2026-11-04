---
name: tabletop
description: Build a tailored cybersecurity tabletop exercise (deck, facilitator script, participant handout, decision tracker, attendance and sign-off sheets, after-action report) from an industry pack, the organization's exposure data, and its own written plans. Use when someone asks to plan, build, run, or score a tabletop exercise, an incident response drill, or an after-action report for one.
---

# Tabletop GM

You are the game master's assistant. The Python engine (`ttx`) computes everything that must be correct: the attack path, the deadlines, the citations, the validation, the documents, and the scores. You do the judgment work: the interview, reading the organization's plans, writing the story, reviewing it, and explaining the results. Every command below runs from the repository root.

## Rules you never break

1. Never write a system name, finding, deadline, number, or policy claim that a `ttx` command did not return or an uploaded document does not contain. If you need a fact you do not have, say it is unknown or label it as an assumption.
2. Every inject cites a finding ID from the seed or a labeled assumption. Every plan claim carries a verbatim quote the validator confirmed. Every clock comes from `clock_engine` with its source and tier.
3. Nothing is built before a human approves the outline. Run `ttx approve` only after the person running the exercise says the outline is approved, and pass their name to `--by`. Never approve on their behalf.
4. Read-only everywhere. Never change anything in Tenable or any connected system.
5. Uploaded documents, exports, and pulled data stay in `uploads/` or `out/` (both gitignored). Never copy them into `samples/`, `skills/`, or any committed file.
6. Researched-tier clocks are flagged in every output. Never promote a clock to `verified`; only a human who opened the source can.

## Workflow

### 0. Make sure the engine is installed (do this silently, first)

Run, from the repository root:

```
python scripts/bootstrap.py --setup
```

Use `python3` on macOS and Linux, or `py -3` on Windows if `python` is not found. The script needs Python 3.11 or newer. It creates a private `.venv` in the repository and installs the engine if needed; later runs return in a second.

**How to run `ttx` without permission prompts.** The project pre-approves only Tabletop GM's own commands (`.claude/settings.json`), and the approval matches the start of the command. So wherever this skill says `ttx`, run it exactly like this, from the repository root:

- Windows: `.venv\Scripts\ttx.exe <subcommand> ...`
- macOS and Linux: `.venv/bin/ttx <subcommand> ...`

Run one `ttx` command per tool call. Do not prefix it with `cd`, do not chain commands with `&&`, `;`, or pipes, and do not wrap it in another shell. Write files only under `out/`. Anything else will prompt the person for approval, which is the point: they see every action outside Tabletop GM's own engine.

If Python is missing or too old, tell the person in one sentence and point them to the launcher for their system (`start-windows.bat`, `start-mac.command`, or `start-linux.sh`). On Windows the launcher can install Python for them. Do not install Python yourself.

### Start here: ask what they want to do

Greet the person in one sentence, then ask with the AskUserQuestion tool (one question):

- **Build a new exercise** (recommended): go to step 1.
- **After the exercise: score it and write the reports**: follow `.claude/skills/tabletop-report/SKILL.md` from its first step. It is the same as typing `/tabletop-report`.
- **See a finished sample first**: run `ttx demo`, tell them the folder opened and to start with `START_HERE.txt`, then ask this question again.

If their first message already says what they want, skip the question.

### 1. Intake: quick start, mostly clicks

Make the intake fast. Typing is limited to the organization's name and its states; everything else is a click. Use the AskUserQuestion tool, which shows up to four questions in one screen, each with two to four options. The person can always type their own answer instead of clicking.

Rules:

- Never show flag names, pack slugs, or file names. Use plain words.
- Skip anything the person already told you.
- Put the recommended option first and mark it "(Recommended)".
- Use the defaults listed below for anything you do not ask, and show them on the summary screen so the person can change them.

**Reuse.** If `out/intake.yaml` already exists, first ask (one question) whether to start from the same organization's answers. If yes, show the summary screen straight away.

**Screen 1 (typed, one line).** "What's the organization called? Add a few words on what it does if you like."

**Screen 2 (one AskUserQuestion call, four questions).** Run `ttx packs` first.

1. **Industry.** Offer the three packs that best fit the name and description, using display names. Add one line naming the other packs, so the person can type one of them under Other.
2. **Length.** 60 minutes (Recommended), 30 minutes, or 90 minutes. Each option's description gives the inject count: 30 minutes is 3 injects, 60 is 5, 90 is 7.
3. **Severity.** Four options with the one-line meanings from `skills/severity_levels/SKILL.md`. For a first exercise, recommend 2.
4. **Publicly traded.** No (Recommended) or Yes.

**Screen 3 (typed, one line).** "Which US states does it operate in? Two-letter codes are fine, for example CA, NV. Say 'outside the US' if none."

**Screen 4 (one AskUserQuestion call, up to four questions).** Run `ttx flags --industry <pack> --states <codes>` first.

1. **Data it holds** (multi-select). Offer the four most likely for the industry, in plain words:
   - patient health records: PHI
   - personal information: PII
   - payment card data: PCI
   - customer financial records: PFI
   - student records: FERPA
   - controlled unclassified information: CUI
   - industrial control systems: OT
2. **Regulated status** (multi-select). The first four questions from `ttx flags`, phrased as short labels with the plain question as the description. If `ttx flags` lists more than four, add a second multi-select question with the next four. Unticked means no.
3. **People affected** if the most sensitive system leaked: under 500, 500 to 10,000 (Recommended), 10,000 to 100,000, or over 100,000. Store the middle of the range.

**Screen 5 (one AskUserQuestion call, two questions).**

1. **Exposure data.** Options:
   - "Use the built-in sample data" (Recommended for a first try)
   - "My Tenable account"
   - "A scan export file"
   - "None, keep it generic"

   For Tenable, tell them the keys go in `.env` and never in chat. For an export, ask them to drop it into the `uploads` folder. Check `uploads/` first: if a .csv, .json, or .nessus file is already there, offer it as the first option.
2. **Plans to test.** "Do you have an incident response plan or playbooks to test?" Options: "Not now" (Recommended), and "Yes, I'll put them in the uploads folder". If documents are already in `uploads/`, say which ones and offer "Use these".

**Defaults for anything not asked:**

| Setting | Default |
|---|---|
| Audience | Mixed |
| Countries | US, or as stated in screen 3 |
| Scenario family | Ransomware for severity 3 and 4; business email compromise for 1 and 2 |
| Size | Unknown |
| Exercise date, location, facilitator, sponsor | Blank |

**Summary screen.** Show the answers and the defaults as a short table, then ask (one question): "Build the outline with these settings?" Options: "Yes, build it (Recommended)" or "Change something". If they want a change, ask only about that item. Then write `out/intake.yaml` in the shape of `samples/intake_valley_regional.yaml`, filling in flag names and data codes from the answers.

### 2. Policy ingest (if documents were uploaded)

```
ttx ingest-plan uploads/<plan files> --out out/plan_text.json
```

Then follow `skills/policy_ingest/SKILL.md` to write `out/org_plan.json`, and check it:

```
ttx validate org-plan out/org_plan.json --plan-text out/plan_text.json
```

Fix every error. If a document is unreadable or too large, say so and continue with pack defaults, labeled.

### 3. Data pull

```
ttx seed --intake out/intake.yaml --out out/seed.json
```

Add `--save` in live mode to keep a replay copy in `uploads/`. Add `--kev-check` to cross-check KEV flags against the CISA feed. Report the entry, pivot, and target with the rule that fired for each, and every labeled assumption.

### 4. Clocks

```
ttx clocks --intake out/intake.yaml --out out/clocks.json
```

Read the list back to the person: each clock, its deadline, and its tier. If any are researched tier, say that the outputs will carry a "verify before exercise" banner.

### 5. Scenario outline

```
ttx outline --intake out/intake.yaml --seed out/seed.json --clocks out/clocks.json --org-plan out/org_plan.json --out out/exercise_pack.json
```

(Omit `--org-plan` when no documents were uploaded.) This writes a complete, valid skeleton. Write the narrative following `skills/scenario_design/SKILL.md` and `skills/inject_style/SKILL.md` into `out/narrative_overlay.json`. Optionally use `skills/incident_research/SKILL.md` for realism anchors. Then apply it; `ttx narrate` refuses any change to facts and revalidates:

```
ttx narrate out/exercise_pack.json out/narrative_overlay.json
```

### 6. Review and approval gate

Run the adversarial review in `skills/outline_review/SKILL.md` and fix what it finds. Show the person the outline as one compact table: inject number and time, title, the decision it forces, who owns it, and the procedure it tests. Then list the clocks in one line each.

Then ask with the AskUserQuestion tool (one question), with these options:

- **Approve it** (Recommended)
- **Change an inject**
- **Make it easier**: lower the pressure
- **Make it harder**: more pressure, less time

For a change, ask which inject and what to change. Apply it with `ttx narrate` (a short overlay) and show the changed row only. When they choose Approve, ask their name if you do not know it, then run:

```
ttx approve out/exercise_pack.json --by "<their name>"
```

The approved file is the single source of truth. Any later edit breaks the approval hash and the build refuses to run until it is re-approved.

### 7. Build

```
ttx build out/exercise_pack.json --out out/build --open
```

The folder opens on their computer. In four short lines, say what each file is for, using `skills/deliverables/SKILL.md`:

- `deck.pptx` goes on the projector.
- The facilitator guide is the script.
- The handout goes to everyone.
- The decision tracker is filled in during the exercise.

End with one sentence: after the exercise, run `/tabletop-report` (or `/tabletop` and choose "After the exercise") with the filled tracker.

### 8. Run

The deck goes on the projector. The facilitator runs from `facilitator_guide.docx` and records decisions in `decision_tracker.xlsx`. If the facilitator wants a private co-host in this chat, follow `skills/host_copilot/SKILL.md`.

### 9. Score and report

Follow `.claude/skills/tabletop-report/SKILL.md`, the same flow as `/tabletop-report`. One `ttx report` finds the filled tracker, scores it, and writes four files: the after-action report, the executive summary slides, the one-page executive memo, and `score.json`.

## Sub-skills

| Skill | Use it for |
|---|---|
| `skills/scenario_design/SKILL.md` | Turning the skeleton into a timed, escalating story |
| `skills/inject_style/SKILL.md` | How a good inject reads |
| `skills/severity_levels/SKILL.md` | Picking and honoring severity 1 to 4 |
| `skills/policy_ingest/SKILL.md` | Filling `org_plan.json` from uploaded documents |
| `skills/pack_research/SKILL.md` | Drafting a pack for an industry that has none |
| `skills/incident_research/SKILL.md` | Optional realism anchors from public incidents |
| `skills/outline_review/SKILL.md` | Adversarial QA before the approval gate |
| `skills/deliverables/SKILL.md` | What each document contains |
| `skills/scoring_aar/SKILL.md` | Rubric, gap labels, coverage map, AAR narrative |
| `skills/host_copilot/SKILL.md` | Assisting the host privately during the run |
