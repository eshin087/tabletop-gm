---
name: tabletop-report
description: After a Tabletop GM exercise, score the filled decision tracker and write the after-action report, the executive summary slides with lessons learned, and a one-page executive memo in one step. Also shows those reports from synthetic demo responses for a pitch or a practice run. Use when the host says the exercise is done, drops in a tracker, asks for the score, the AAR, or a summary for leadership, or wants to demo the reports.
allowed-tools: PowerShell(.venv\Scripts\ttx.exe *) Bash(.venv/bin/ttx *) Bash(.venv/Scripts/ttx.exe *)
---

# Tabletop GM: after the exercise

Turn the host's filled decision tracker into the reports, with as little effort as possible. The engine does the scoring and writes every document; you find the files, run one command, and explain the result in plain words.

## 1. Make sure the engine is installed (silently)

```
python scripts/bootstrap.py --setup
```

Use `python3` on macOS and Linux, or `py -3` on Windows if `python` is not found. Then run `ttx` exactly as `.venv\Scripts\ttx.exe ...` on Windows or `.venv/bin/ttx ...` on macOS and Linux, from the repository root, one command per call.

## 2. Real results or demo responses

If the person already said they want a demo, a pitch, or a practice run, skip the question and go to "Demo responses" below. Otherwise ask with the AskUserQuestion tool (one question), "Which responses should the reports use?":

- **The filled tracker from our exercise** (Recommended): go to "Find the tracker".
- **Demo responses, for a pitch or a practice run**: go to "Demo responses".

### Demo responses

```
ttx report --demo --open
```

It applies the invented answers in `samples/demo_responses/responses.yaml` to the approved exercise in `out/`, or to the built-in sample exercise if there is none, and writes the reports to `out/report_demo/`. Every page is marked "DEMO: synthetic responses". Say so in your first sentence, every time: these are not results, and nobody should present them as findings. A real `ttx report` never reads the demo tracker, and demo files never go to `out/report/`. Then go to step 3.

### Find the tracker

First, simply try:

```
ttx report
```

It finds the approved exercise (`out/exercise_pack.json`) and the newest filled tracker built for that exercise in `uploads/` or `out/`. It ignores trackers from other exercises and empty ones.

If it says it cannot find a filled tracker, ask the host in one sentence to do one of these, then run it again:

- drag the saved tracker file into this chat, which pastes its path: `ttx report --tracker "<path>"`
- or save the tracker into the `uploads` folder and say "done"

If the tracker is still open in Excel, ask them to save it first. Unsaved answers are not in the file.

## 3. Tell them the result (short)

From the command's output, in this order:

1. For a demo, first say that the results come from synthetic responses.
2. The headline sentence and the overall readiness rating.
3. Lessons learned: what worked and what to improve, one line each, as the command printed them.
4. The files in `out/report/` (or `out/report_demo/`):
   - `executive_summary.pptx`: seven slides for senior management, including lessons learned
   - `executive_summary.docx`: a one-page memo to send ahead
   - `after_action_report.docx`: a short report (result, lessons learned, decision by decision, deadlines, action plan) with the auditor detail in an appendix
   - `score.json`: the engine's record

Offer to open the folder with `ttx report --open`.

## 4. Optional: sharpen the headline for leadership

If the host wants it, write `out/narrative.json` with a `headline` and up to three short `summary` paragraphs, following `skills/scoring_aar/SKILL.md`. Then rebuild:

```
ttx report --narrative out/narrative.json
```

Any number that is not in the score or the exercise is rejected, so use only figures from the output.

## Never

- Never change the tracker's answers or the score. If the host says an answer is wrong, ask them to fix it in the tracker, save, and run `ttx report` again.
- Never name individuals in the summary; name roles.
- Never claim a deadline is verified. Unverified deadlines are marked in every report.
