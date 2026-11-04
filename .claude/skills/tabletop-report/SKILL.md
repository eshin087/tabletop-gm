---
name: tabletop-report
description: After a Tabletop GM exercise, score the filled decision tracker and write the after-action report, the executive summary slides, and a one-page executive memo in one step. Use when the host says the exercise is done, drops in a tracker, or asks for the score, the AAR, or a summary for leadership.
allowed-tools: PowerShell(.venv\Scripts\ttx.exe *) Bash(.venv/bin/ttx *) Bash(.venv/Scripts/ttx.exe *)
---

# Tabletop GM: after the exercise

Turn the host's filled decision tracker into the reports, with as little effort as possible. The engine does the scoring and writes every document; you find the files, run one command, and explain the result in plain words.

## 1. Make sure the engine is installed (silently)

```
python scripts/bootstrap.py --setup
```

Use `python3` on macOS and Linux, or `py -3` on Windows if `python` is not found. Then run `ttx` exactly as `.venv\Scripts\ttx.exe ...` on Windows or `.venv/bin/ttx ...` on macOS and Linux, from the repository root, one command per call.

## 2. Find the tracker

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

1. The headline sentence and the overall readiness rating.
2. The top three risks, one line each.
3. The four files in `out/report/`:
   - `executive_summary.pptx`: slides for senior management
   - `executive_summary.docx`: a one-page memo to send ahead
   - `after_action_report.docx`: the full report for the security team and auditors
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
