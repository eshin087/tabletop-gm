# Tabletop GM: working rules for Claude Code

Read `docs/BUILD_SPEC.md` before doing anything; it is the source of truth and supersedes this file where they differ.

## Non-negotiables
- Deterministic engine first, model on top. Code computes the attack path, the deadlines, the scores, the citations, and the validation. The model writes narrative and judgment. Never let the model produce a system name, a deadline, or a policy claim that a tool didn't return or a document didn't contain.
- Every inject cites a finding ID from the seed or a labeled assumption. Every clock has a source URL, a verified date, and a tier (`verified` or `researched`). Every org-plan item carries a verbatim quote the validator confirms exists in the source. Builds fail otherwise.
- Human approval gate before any deliverable is built. The approved outline is `exercise_pack.json`; every output and the host console read only that file.
- Read-only against Tenable and every other external system.
- No secrets, no real company names, no real employer data, no uploaded policies, and no raw lab exports in the repo, ever. `.env` and `uploads/` are gitignored from the first commit. Samples are synthetic.
- Pure-Python dependencies only (python-pptx, python-docx, openpyxl, pyyaml, pypdf, jinja2; pytenable optional). No Docker, Node, databases, cloud services, or accounts. The host console is a self-contained `host.html`; `ttx host` uses the standard library.
- README claims must match what actually runs. Every command in the README must work in a clean environment. Keep the five required sections: what it does, prerequisites, how to run, outputs, known limitations.
- Keep scenario and file names clearly defensive (no "payload", "exploit", "attack tool").
- Don't use em dashes in prose or documentation.

## Priorities (deadline: PR opened Wednesday Nov 4, 11am PT; target 10am)
1. `seed_engine`, `clock_engine`, `plan_ingest`, `validators`, `cli`, tests, synthetic sample estate and sample IR plan
2. `score_engine`, generators (deck, guide, handout, tracker, sign-in, AAR), one complete sample run in `samples/outputs/`
3. README, SECURITY.md, `SKILL.md` and sub-skills, packs (healthcare and banking verified; others researched or stubbed and listed as roadmap)
4. After the PR: `host.html` generator (host's laptop console; audience sees only the deck), then optional `ttx host` with the AI co-host

## When unsure
Prefer the honest, smaller scope. Label assumptions. Ask Eric only about decisions the spec doesn't already settle. Tenable is optional: live mode reads `TENABLE_ACCESS_KEY` and `TENABLE_SECRET_KEY` from `.env`; export and sample-estate modes need no keys.
