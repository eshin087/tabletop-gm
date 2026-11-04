# Decisions log

Blockers hit during the build and the option chosen, newest first. Each entry says what the spec or prompt asked for, what was found, and what was done instead.

## 2026-11-03

- **Repository owner.** The prompt asked for `gcd/tabletop-gm`. The authenticated gh account is `eshin087` (display name "gcd", a personal account, no underscore). The GitHub login `gcd` belongs to a different user and no `gcd` organization is available to this account. The repo was created as `eshin087/tabletop-gm` so commits stay under Eric's personal account. LICENSE and Exchange metadata still name the author as gcd.
- **Lab exports.** The prompt asked to move the lab exports into `uploads/`. The build folder contained only `BUILD_SPEC.md` and `CLAUDE.md`; no export files were present. `uploads/` was created empty and gitignored. The export parser is built from the field names recorded in `docs/BUILD_SPEC.md` section 7, as the spec instructs.
- **gitleaks.** Not installed; brew and apt are not available on this Windows machine. Installed with `winget install --id Gitleaks.Gitleaks` (release binary 8.30.1).
- **Clock verification tier.** The spec targets `verified` for healthcare and banking. A verified clock means a human checked it against the primary source on the recorded date. Claude Code drafted every clock, so every clock ships at the `researched` tier with its primary source URL. Promoting a clock is a one-line edit (`tier: verified`, `verifier: <name>`, `verified_date: <date>`) after a human opens the source. The sample outputs therefore carry the "verify before exercise" banner, which also demonstrates the feature.
- **Host console.** `host.html` and `ttx host` are Phase 2 (after the PR) per CLAUDE.md priority 4 and are listed as roadmap in the README.
