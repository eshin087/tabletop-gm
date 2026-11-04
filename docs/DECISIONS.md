# Decisions log

Blockers hit during the build and the option chosen, newest first. Each entry says what the spec or prompt asked for, what was found, and what was done instead.

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
