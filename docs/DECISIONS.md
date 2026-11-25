# Decisions log

Blockers hit during the build and the option chosen, newest first. Each entry says what the spec or prompt asked for, what was found, and what was done instead.

## 2026-11-23 (host console)

- **`ttx host` and `host.html` ship.** These were the spec's Phase 2 (section 14) and the top two roadmap items. Decisions:
  - **One page, two ways to run.** `ttx/host/console.html` is served by `ttx host` and written by `ttx build` as `host.html`. Served, every click is one `ttx.decision_log` call. Standalone, the page builds the same log shape in the browser and exports it. A log exported from a real browser is kept as a test fixture (`tests/data/host_html_export.json`), and a test requires `ttx report --log` to score it.
  - **No server state.** The console derives the current inject, the clock answers, and the end of the exercise from the pack and the log. That is what makes `--resume` and `--replay` simple, and it means the screen cannot disagree with the record.
  - **The co-host uses the official `anthropic` package as an optional extra.** The spec asked for a standard-library server with zero extra dependencies. The server, the page, capture, replay, and scoring are standard library plus the existing engine, and they work with no key. Only the co-host needs `pip install -e ".[host]"`. Writing the API calls by hand over urllib was rejected: streaming, retries, and the fallback for a declined request are the SDK's job, and an optional extra is how `pytenable` is already handled. CLAUDE.md's dependency rule now says so.
  - **The co-host suggests and the host confirms.** The spec has the co-host map a note onto the expected-action checkboxes. Its answer is requested as structured output whose schema lists the pack's own role, action, and party ids, so an id from outside the pack cannot come back. `clean_suggestion` filters again, and the engine validates a third time when the host clicks Log.
  - **Never reveal, by construction.** A line written for the room is built from the exercise frame and the current inject only. Later injects, `what_good_looks_like`, and `where_teams_fail` are not in the request, and a test asserts it.
  - **A deterministic check on every AI line** (`ttx/host/conduct.py`). It covers numbers, identifiers that contain a digit, durations as written or as derived from a pack deadline (so "60 days" matches 1,440 hours), and five-word runs from a later inject or an expected answer. The room's own words are allowed back. It cannot catch an invented name with no digit in it, and the README says so. A flagged line is shown with a warning instead of being hidden, because the console is the host's private screen and the host decides what to say.
  - **Default model and fallback.** The co-host calls `claude-opus-5-5` at low effort, with a server-side fallback so that a request a safety classifier declines by mistake (the content is a security exercise) is retried on the recommended model. A refusal or an API error falls back to the pack's script line and tells the host why. `TTX_HOST_MODEL`, `TTX_HOST_EFFORT`, `TTX_HOST_FAST`, and `TTX_HOST_AI` change the defaults.
  - **Local server hardening.** Bound to 127.0.0.1, Host header checked, a random per-run token on every API call, no CORS headers. The test suite blocks sockets, so the HTTP layer is tested through an in-memory socket and the routes through `App.handle`.
  - **Replay is read-only.** `ttx host --replay LOG` copies the log, steps through it with a cursor in the page, and can score it. It never appends, and a test checks the original file's hash.
  - **A finished session shows its score again.** When a server is started with `--resume` on a session that has ended, it rebuilds the scorecard from the log. Scoring is deterministic, so this is safe.
  - **Two screens.** The first console put the script, the answers, the form, the clocks, and the log on one page. That was too much to follow while running a room, and it could not go on a projector because it held the answers. `ttx host` now serves a room screen at `/room` and keeps the host console private. Everything the room screen shows comes from one module, `ttx/host/room.py`, which never includes expected actions, plan quotes, the clock table, an inject that has not been presented, or a system the story has not reached. A test serializes the whole payload and searches it.
  - **The host console is a guided sequence.** Read, Discuss, Record, and the clocks once. There is one primary button per step and Space advances. The reference material is folded and marked private.
  - **The wall waits for the fact check.** This reverses the choice above to show a flagged line with a warning. On a private screen the host can judge a flagged line. On a wall the room has already read it. An AI line is held until `conduct.check_text` passes, and a flagged or declined line is replaced by the pack's script line. A stakeholder line must also parse as a role the pack defines followed by a quoted sentence.
  - **One piece of server state.** The line currently on the wall lives in memory, because an AI line is not part of the record. After a restart the wall shows the script line. Everything else is still derived from the pack and the log, and a replay keeps its position on the server only so the two screens agree.
  - **The room screen needs no token.** It has to open in a second window that never saw the console page. It is read-only, bound to 127.0.0.1, Host-checked, and carries only the room's view.
  - **The attack path follows what the room was told.** The sample's second inject cites the entry finding while telling the room the attacker is on the domain controller. The wall reveals a system when an inject cites its finding or names it in the title, the line read aloud, or the decision, so the picture never lags the story and never names a system early.
  - **No room view.** The spec's room setup keeps the audience on the deck, so the console is the host's private screen and shows the expected answers. A projector view with no spoilers is on the roadmap.
  - **Not built: a practice mode in which a model plays the room.** It needs a live model to mean anything, and no automated test can call one. It is on the roadmap.
  - **A seventh generator.** `ttx build` now writes `host.html`, so the two tests that counted six outputs count seven. `samples/outputs/host.html` was built with `ttx build --only host`; the other committed sample outputs were not regenerated.
  - **Launcher option 4** opens the console with no Claude account, on the user's own exercise when one is built and on the sample otherwise, in the first unused `out/host` folder.

## 2026-11-04 (demo responses and a shorter AAR)

- **Demo responses for pitches.** Eric needs to show the after-exercise reports without running an exercise first. `samples/demo_responses/responses.yaml` holds invented answers written with tokens (`owner`, `other`, `all_but_last`, `{entry}`) instead of names, so one file fits any approved exercise. `ttx report --demo` fills a tracker from it, scores it, and writes to `out/report_demo/`, falling back to the built-in sample exercise when `out/` has none. Every output is marked "DEMO: synthetic responses", and the demo tracker is named so a real `ttx report` never picks it up. `/tabletop-report` asks whether to use the real tracker or demo responses.
- **Shorter after-action report.** The AAR ran about 6,700 words before the evidence page, and readers could not find the actions. The body is now about two pages: the result, lessons learned, one row per decision, the deadlines, and an action plan that groups gaps sharing a fix into one row with the gap ids it closes. Everything the spec requires for auditors (scores by dimension, the plan coverage map, every gap with its citation, the evidence page, the rubric) moved to an appendix, unchanged in content.
- **Lessons learned.** The AAR, the executive deck (now seven slides), and the memo add "What worked" and "What to improve". Both lists are built from the score by fixed rules, so they add no fact the score does not hold. The memo swaps its risks section for lessons learned to stay on one page.

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
  - **One entry point.** Live mode is a choice in the `/tabletop` start menu and launcher option 3, not a separate command to learn. With no exercise built, it offers the approved sample pack, so a fresh download can try it at once. `ttx report --log` exports, scores, and writes the AAR and executive summary in one step.
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
- **Host console.** `host.html` and `ttx host` are Phase 2 (after the PR) per CLAUDE.md priority 4 and are listed as roadmap in the README. The `host_copilot` skill works today in a Claude Code chat beside the facilitator guide. (Shipped on 2026-11-23; see the entry at the top.)
