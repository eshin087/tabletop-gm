# Decisions log

Blockers hit during the build and the option chosen, newest first. Each entry says what the spec or prompt asked for, what was found, and what was done instead.

## 2026-11-04 (prep and report experience)

- **Lengths are 30, 60, or 90 minutes.** The spec had 60, 90, and 180. Eric asked for shorter options, so the engine now builds 3, 5, or 7 injects.
  - The 30-minute exercise runs escalation, the business tradeoff, and notification.
  - The 60-minute exercise swaps recovery for the tradeoff, so the ransom decision and the plan-silent inject stay in.
- **Quick-start intake.** In testing, the one-question-at-a-time interview felt long. The intake now uses Claude Code's multi-question screens of clickable choices; typing is limited to the organization's name and its states. Unasked settings use defaults shown on a summary screen, and the interview can reuse an earlier `out/intake.yaml`.
- **Host-friendly tracker.** The tracker is now one color-coded block per inject:
  - plain questions with dropdowns, and Yes/No per expected action and notification instead of typed IDs
  - a Notification clocks sheet with owner and timing dropdowns
  - hidden machine keys in column A, so scoring stays exact

  The CSV decision-log format (`schemas/tracker_columns.yaml`, `DECISION_COLUMNS`) is unchanged, so the live GM feature's `ttx log export` keeps working. The earlier one-row-per-inject `.xlsx` is still read.
- **One step after the exercise.** `ttx report` finds the approved exercise and the newest filled tracker built for it, using the approval hash stored in the tracker. It writes the score, the after-action report, and the executive summary together. `/tabletop-report` and a "After the exercise" option in the `/tabletop` start menu guide the host. `ttx aar` is unchanged, which leaves room for the live GM feature's `--log` flag.
- **Executive summary.** Senior management gets six slides and a one-page memo, built from the same deterministic content as the AAR:
  - a plain-language bottom line
  - fixed rating thresholds: Strong at 85% and up, Adequate at 70 to 84%, Needs work below 70%
  - regulatory exposure and the top three risks
  - the top five fixes, with owners and dates
  - the decisions needed from leadership

  It has no finding IDs.
- **Pre-approved commands.** `.claude/settings.json` pre-approves only:
  - the project's `ttx` engine
  - `scripts/bootstrap.py`
  - file edits under `out/`

  The two skills also declare the engine in `allowed-tools`. Claude Code applies project allow rules only after the person accepts the folder's trust prompt, which lists them.

## 2026-11-04

- **Live GM mode.** A third way to run the exercise: Claude facilitates in the Claude Code chat with the chat on the projector, per `docs/LIVE_GM_ADDENDUM.md`. Decisions:
  - **Fresh session on exercise day.** The prep chat holds the expected answers and scoring notes, so the live run happens in a new session that reads only the approved pack. The skill stops if it finds prep content in the chat.
  - **Unplanned entries are logged but never scored.** The rubric covers planned decision points only; `--unplanned` entries appear in the AAR timeline so the record is complete while the score stays deterministic.
  - **The export reuses the tracker shapes.** `ttx log export` writes `decisions.csv` and `decisions_clocks.csv` in exactly `schemas/tracker_columns.yaml`, so `ttx score` and `score_engine` are untouched. The JSON log is the audit original; corrections append a new version and mark the old one `superseded_by`.
  - **Ids are validated, parties too.** The addendum refuses unknown inject, role, and action ids. Unknown notified-party ids are refused as well, so nothing the pack does not name reaches the record; `--note` is the escape hatch.
  - **Session end is the last entry.** There is no `ttx log end`; the facilitate skill logs an "Exercise ended" note, and the AAR appendix reports the last entry's time as the end.
  - **No MCP server.** `ttx log` is a CLI group the skill calls, like every other engine function. An MCP wrapper stays on the roadmap.
- **Intake is one question at a time.** The spec asked for a single intake message. In testing, Eric found that a single message of questions overwhelms people, so the `/tabletop` intake now asks one short question per message and waits for the answer. It uses Claude Code's clickable choices where it can, skips what it already knows, and accepts "not sure" with a stated default. Regulated statuses come from `ttx flags`, which turns every clock flag into a plain yes/no question (`schemas/flags.yaml`) and drops statuses for states the organization does not operate in. A test fails if a clock uses a flag with no question.
- **One-click launchers.** First-time users download the ZIP and double-click `start-windows.bat`, `start-mac.command`, or `start-linux.sh`. The launcher sets up a private `.venv` and shows a two-option menu. `/tabletop` also installs the engine itself when needed.

## 2026-11-03

- **Scenario clocks.** `ttx clocks` returns every clock that applies to the organization. The outline keeps only the clocks the scenario's crown-jewel data can trigger. For example, a PHI database breach does not start the Visa card clock. Dropped clocks are listed in `clocks_outside_scenario` with the reason. This keeps the notification inject and the AAR honest about what the scenario exercised.
- **Chained clocks.** Some agency notices run from the notice to individuals, not from discovery (California AG sample copy, Oklahoma AG, the Visa incident report). These carry `after_clock`. The scorer measures them from the parent clock's planned notice, and the clock engine does the same from its timestamp. "Concurrent with" and "prior to" notices are not chained; they are listed as a known limitation.
- **NYDFS scope.** The insurance pack's NYDFS 500.17 clocks were limited to the insurance industry. Part 500 covers every DFS-licensed entity, so the industry limit was removed and the `nydfs_licensed` flag alone decides.
- **Duplicate Visa clock.** The retail pack and the common file both carried the Visa three-day notice. The common copy was kept, and the retail incident-report clock now chains from it.
- **Sample approval and tracker.** The committed sample exercise is approved by "Sample approver (synthetic run; a human signs here in real use)", and its completed tracker is invented. Both exist so reviewers can rebuild and re-score without a model. Real use requires a human to run `ttx approve`.
- **Skill registration.** The spec puts the entry skill at the repository root (`SKILL.md`). Claude Code registers project skills from `.claude/skills/<name>/SKILL.md`. A thin `.claude/skills/tabletop/SKILL.md` makes `/tabletop` work from a clone and points to the root file. The ten sub-skills are read by path at the step where each applies, so they need no registration.
- **KEV cross-check.** The spec asks to cross-check the Tenable KEV flag against the CISA feed when it is reachable. This is opt-in (`ttx seed --kev-check`) so the default run makes no network call. `--kev-file` checks against a local copy instead.
- **Repository owner.** The prompt asked for `gcd/tabletop-gm`. The authenticated gh account is `eshin087`, a personal account with display name "gcd" and no underscore. The GitHub login `gcd` belongs to a different user, and no `gcd` organization is available to this account. The repo was created as `eshin087/tabletop-gm` so commits stay under Eric's personal account. LICENSE and the Exchange metadata still name the author as gcd.
- **Lab exports.** The prompt asked to move the lab exports into `uploads/`. The build folder contained only `BUILD_SPEC.md` and `CLAUDE.md`; no export files were present. `uploads/` was created empty and gitignored. The export parser is built from the field names recorded in `docs/BUILD_SPEC.md` section 7, as the spec instructs.
- **gitleaks.** It was not installed, and brew and apt are not available on this Windows machine. It was installed with `winget install --id Gitleaks.Gitleaks` (release binary 8.30.1).
- **Clock verification tier.** The spec targets `verified` for healthcare and banking. A verified clock means a human checked it against the primary source on the recorded date. Claude Code drafted every clock, so every clock ships at the `researched` tier with its primary source URL.
  - Promoting a clock is a one-line edit after a human opens the source: `tier: verified`, `verifier: <name>`, `verified_date: <date>`.
  - The sample outputs therefore carry the "verify before exercise" banner, which also demonstrates the feature.
  - www.ecfr.gov blocks automated fetching, so CFR text was confirmed on the law.cornell.edu mirror. Each such clock says so in its notes.
- **Research findings that changed the brief.** Recorded so a verifier checks these first:
  - The TSA pipeline report is now 72 hours under SD Pipeline-2021-01G, not 24.
  - California Civil Code 1798.82 now sets 30 calendar days.
  - FedRAMP is moving to tiered deadlines in 2026.
  - The CIRCIA final rule is not yet effective.
  - The Visa notice is three calendar days, not business days.
- **Host console.** `host.html` and `ttx host` are Phase 2 (after the PR) per CLAUDE.md priority 4 and are listed as roadmap in the README. The `host_copilot` skill works today in a Claude Code chat beside the facilitator guide.
