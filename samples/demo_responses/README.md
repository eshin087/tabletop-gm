# Demo responses (synthetic)

`responses.yaml` holds invented answers for a tabletop exercise, so you can show the after-exercise reports in a pitch or a practice run without holding a real exercise.

## Use it

In Claude Code, type `/tabletop-report` (or `/tabletop` and choose "After the exercise") and pick "Use demo responses". Or run it directly from the repository root:

```
ttx report --demo --open
```

It applies these answers to the approved exercise in `out/`. If there is none, it uses the built-in sample exercise. Then it scores the result and writes everything to `out/report_demo/`:

- `executive_summary.pptx`: slides for senior management, including lessons learned
- `executive_summary.docx`: the one-page memo
- `after_action_report.docx`: the short after-action report, with the auditor detail in an appendix
- `score.json` and `demo_tracker.xlsx`: the score and the filled demo tracker behind it

Every page is marked **DEMO: synthetic responses**. The demo tracker is never picked up by a real `ttx report`, and demo results never go to `out/report/`.

## How the answers fit any exercise

The answers don't name roles, systems, or plan steps. They use tokens such as `owner`, `other`, `all_but_last`, and `{entry}`, which the engine fills in from the approved exercise. The comments at the top of `responses.yaml` list every token. The answers describe a capable team with realistic gaps: fast detection, a slow declaration, one decision made by the wrong role, and one notice nobody planned. On the sample exercise, this lands in the "Adequate" band.

Edit `responses.yaml` to tell a different story. Keep speed, plan step, and documented to the tracker's dropdown text.
