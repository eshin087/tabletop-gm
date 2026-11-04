# Tabletop GM: Build Spec v2 (final for Claude Code, Nov 3, 2026)

Consolidated from Eric's design decisions, Eric's build spec (Nov 3), the Exchange reviewer checklist, and Eric's Nov 3 answers. This is the document Claude Code works from. Decisions in this version supersede the project instructions where they differ.

## 1. What we're building

Tabletop GM turns a two-week, $20K to $50K consultant engagement into an afternoon. It builds a cybersecurity tabletop exercise that is tailored three ways: to the organization's **industry and regulators** (an industry pack with verified notification clocks and exercise requirements), to the organization's **real exposure** (Tenable One API, an uploaded scan export, or a synthetic sample estate), and to the organization's **own written policies** (uploaded IR plan, BCP/DR plan, playbooks, procedures, communication templates). It outputs everything the exercise needs: deck, facilitator script, participant handout, decision tracker, attendance and sign-off sheets, and an after-action report with scores, gap labels, a plan coverage map, and an evidence page for auditors and regulators.

Why it's different: commercial AI tabletop products and CISA's exercise packages use generic incident stories. Consultants tailor by hand over weeks. Tabletop GM builds the scenario from the organization's actual attack path and tests the organization's actual procedures, which is exactly what auditors and regulators scrutinize: are you following your written plan.

Phase 2: the audience only ever sees the slide deck. The host runs a second laptop with a self-contained `host.html` (script, click-based decision capture, timer, optional transcription) and, with an API key, a local AI co-host. No server, no scribe. Install story: `pip install` to build exercises, double-click a file to run one, Claude Code or an API key only for the AI parts. No Docker, no Node, no database, no cloud, no accounts.

## 2. Decisions (Nov 3)

- Name: **Tabletop GM**, slug `tabletop-gm`, listing file `skills/tabletop-gm.md`
- Entrant: Eric (gcd) is the registered participant, listing author, and sole team member
- Deadline: PR opened by Wednesday Nov 4, 11am PT (organizers). Opened counts. We then merge so the product is live for the demo and make later edits with new PRs
- Room setup: the audience sees only the .pptx on the projector; the host has a separate laptop running `host.html` for the model engagement and transcription. Phase 2 is attempted for Thursday: `host.html` first, AI co-host via `ttx host` second; fallback is the facilitator guide read aloud
- Tenable data is an optional mode, never a requirement; the user enables it by putting API keys in `.env`, and the product pulls the data itself. The demo runs live with Eric's lab keys; an export file is the fallback if the API is unreachable
- Industries: as many as normally run tabletops, with a two-tier verification model (section 8)
- New feature: policy and procedure upload tailors the script and scoring to the organization's own plans (section 9)

## 3. Scope by phase

| Phase | What ships | When |
|---|---|---|
| 1. Prep artifacts (the PR) | Intake, policy ingest, data pull, seed, clocks, scenario outline, human approval gate, all documents, tracker, scoring, AAR | PR by 10am PT Wednesday |
| 2. Host console and AI co-host | `host.html` on the host's laptop with click-based decision capture (no scribe, no server); then `ttx host` with the AI co-host as the stretch | Wednesday afternoon and Thursday morning |
| 3. Roadmap | Voice host (speech-to-speech API), Slack/Teams rooms, adaptive attacker, quarterly reruns on unfixed paths, community industry packs | After SWARM |

One scenario per exercise, designed fresh from intake, pack, exposure data, and the organization's policies. No fixed scenario list.

## 4. Form and listing

Primary listing: **Skill** (Claude Code, `/tabletop`). The agent is Claude Code running the skill set; the intake happens in chat; the Python engine does everything that must be correct; deliverable generators are scripts, so reviewers rebuild every output from the sample pack with zero credentials and no model call. No MCP server for Wednesday; the engine's functions are CLI entry points the skill calls (an MCP wrapper is a one-hour add later for a third listing). The Phase 2 host becomes an **Agent** listing later if it matures.

Exchange metadata: name "Tabletop GM", author gcd, license MIT, tier contributed, domains ["security-awareness", "security-operations"], integrations ["Anthropic", "Tenable"], works_with_tenable_hexa_mcp false, compatible_platforms ["Claude Code"], invocation "/tabletop", tags: tabletop, incident-response, exercise, after-action-report, nist-800-61, industry-packs, policy-testing.

## 5. User workflow

1. **Intake** (one message, the skill asks only for what's missing): organization name and size; industry; countries and states of operation; data types held; public or private; regulated status details (for example NY-licensed, federal contractor, PCI merchant level); severity level 1 to 4; audience (technical, executive, mixed); duration (60, 90, 180 minutes); optional scenario family preference; optional document uploads as Word or PDF (IR plan, BCP/DR plan, playbooks, procedures, comms templates; scanned PDFs needing OCR are roadmap); environment data mode (Tenable API, export upload, sample estate).
2. **Policy ingest** (if documents uploaded): `plan_ingest` extracts text with section anchors; Claude fills `org_plan.json` (roles, severity definitions, escalation paths, notification procedures, RTO/RPO, decision authorities, comms templates, playbook steps) with a verbatim quote and location for every item; `validate` rejects any item whose quote isn't in the source.
3. **Data pull**: `seed_engine` returns the scenario seed (entry, pivot, crown jewel) with finding IDs, CVEs, VPR, KEV flag, criticality, and the rule that fired for each choice. No data means a generic scenario with every assumption labeled.
4. **Clocks**: `clock_engine` returns the applicable notification deadlines (industry, jurisdictions, data types, public/private, regulated status), each with source link, verified date, and verification tier.
5. **Scenario outline**: Claude writes the outline from the seed, the pack, and the org plan using `scenario_design`; each inject names the procedure it tests; `validate` rejects anything incomplete or uncited.
6. **Approval gate**: the prepper reviews, edits, and locks the outline. Nothing is built before sign-off. The locked outline becomes `exercise_pack.json`, the single source of truth for every output and for the Phase 2 host.
7. **Build**: generators produce the deck, facilitator guide, handout, tracker, attendance and sign-off sheets, and `host.html`.
8. **Run**: the deck goes on the projector; the host opens `host.html` on a separate laptop, follows the script inject by inject (aligned by inject and slide number), and captures decisions with clicks; with `ttx host` and a key, the AI co-host assists privately. Phase 1 fallback: facilitator guide plus the .pptx.
9. **Score and report**: `score_engine` scores the tracker against the org plan's expected steps (or pack defaults when no plan was uploaded); Claude writes the AAR from its numbers using `scoring_aar`, including the plan coverage map.

## 6. Architecture

```
tabletop-gm/
  README.md                 what it does, prerequisites, how to run, outputs, known limitations, roadmap
  SECURITY.md               every outbound call documented: Tenable API (read-only), CISA KEV feed, Anthropic via Claude Code, web research in pack_research (user-initiated)
  LICENSE                   MIT
  SKILL.md                  entry skill: intake, workflow, rules, approval gate
  skills/
    scenario_design/SKILL.md     attack path + org plan -> timed, escalating story; inject rules
    inject_style/SKILL.md        how a good inject reads: voice, pacing, realism, examples (Eric's craft)
    severity_levels/SKILL.md     levels 1 to 4
    policy_ingest/SKILL.md       how to fill org_plan.json from uploaded documents, citation rules
    pack_research/SKILL.md       how to research a sector's regulations from authoritative sources and draft a pack with citations (unverified until a human checks)
    incident_research/SKILL.md   two recent public incidents in the sector, cited, as realism anchors for the narrative (optional, prep only)
    outline_review/SKILL.md      adversarial QA before the approval gate: realism, escalation rules, business tradeoff present, plan coverage, uncited claims
    deliverables/SKILL.md        what each document contains, slide by slide
    scoring_aar/SKILL.md         rubric, gap labels, plan coverage map, AAR structure
    host_copilot/SKILL.md        Phase 2: map a transcript or note onto expected actions, suggest one probing question, never add facts
    industry_packs/
      _template/pack.md + clocks.yaml
      healthcare/, banking/, ... (section 8)
  ttx/
    seed_engine.py          Tenable API | export (CSV, JSON, .nessus) | sample estate -> seed.json
    clock_engine.py         industry + jurisdictions + data types + flags + timestamps -> applicable clocks, met/missed by hours
    plan_ingest.py          docx/pdf/md -> text with section and page anchors; quote verification
    score_engine.py         tracker.xlsx + org_plan.json (or pack defaults) -> scores, totals, gap labels, coverage map
    validators.py           seed, packs, org_plan, injects, exercise pack schema -> pass/fail with reason
    build/                  deck.py (python-pptx), guide.py, handout.py, aar.py (python-docx), tracker.py, signin.py (openpyxl), hostconsole.py (self-contained host.html from a Jinja2 template)
    host/                   Phase 2 optional: stdlib HTTP server for ttx host, AI co-host (maps notes to expected actions, suggests probing questions), decision recorder
    cli.py                  ttx ingest-plan | seed | clocks | validate | build | score | host
  schemas/                  seed.json, org_plan.json, exercise_pack.json, tracker columns, clocks.yaml
  samples/
    synthetic_estate.json          runs with zero credentials
    intake_valley_regional.yaml    fictional 1,200-employee health system
    sample_ir_plan.md              synthetic IR plan so policy ingest can be demonstrated
    exercise_pack_sample.json
    outputs/                       one complete run: deck, guide, handout, tracker, sign-in, AAR, host.html
  tests/
```

Division of labor: code computes facts and does the repetitive work (parsing exports, picking the attack path, computing deadlines, validating citations, building every document, scoring); skills carry the model's method for the judgment work (interviewing, researching a regulator or a recent incident, reading a policy document, writing injects, reviewing an outline, writing the AAR, assisting the host). Ten skills, one job each. Claude never writes a number, deadline, system name, or policy claim a tool didn't return or a document didn't contain.

## 7. Environment data

| Mode | How | Result |
|---|---|---|
| Live | `seed_engine` calls the Tenable VM / Tenable One API with read-only keys from `.env` | Scenario built on current exposure |
| Export | User uploads a findings export (CSV or JSON) and optionally an asset export; .nessus supported if time | Same quality, no tool access needed |
| None | Intake answers only | Generic scenario, every assumption labeled |

Demo rule: the Thursday demo runs in live API mode with Eric's lab keys in `.env` (never committed). Before the pitch, `ttx seed --save` writes the pulled data to `uploads/` (gitignored) so the same run can be replayed in export mode if the API is unreachable on stage. No lab data ships in the repo; the synthetic sample estate is hand-written with the same field names. Pitch language: "exposure data from your scanner, Tenable supported first," never "requires Tenable." Export mode is the path to other scanners (Qualys, Rapid7) through the same column mapping.

Pulled or read: findings on internet-facing assets (asset, plugin, CVE, VPR, severity, first/last seen; KEV flag from `plugin.vpr.on_cisa_kev`, cross-checked against the CISA KEV JSON feed when reachable); asset criticality (ACR) and exposure score; tags for business context; attack paths from Tenable One where available, else an inferred path labeled as such. Column mapping is config-driven with fuzzy header matching so Tenable's CSV and JSON exports both load.

Field names verified against a T1 lab export on Nov 3 (the export itself is not in the repo or the build folder; build the parser from these names): 5,175 critical/high findings on 105 assets, 643 KEV-flagged, VPR on 4,403, EPSS on 4,393; 1,399 assets, ACR present on all via `ratings.acr.score` (top-level `acr_score` on 293), `exposure_score` on 293, 11 assets with public IPv4, one tag (`Exposure: Internet`), 1,101 OT devices from OTSensor, 3 AWS and 3 Azure instances, `installed_software` as CPE strings. Key fields: findings `finding_id`, `asset.uuid` (join key), `asset.hostname`, `asset.device_type`, `asset.operating_system`, `plugin.id/name/cve`, `plugin.vpr.score`, `plugin.vpr.on_cisa_kev`, `plugin.epss_score`, `plugin.exploit_available`, `severity`, `state`, `first_found`, `port.*`, `source`; assets `id`, `hostnames`, `fqdns`, `ipv4s`, `ratings.acr.score`, `exposure_score`, `tags[].key/value`, `system_types`, `operating_systems`, `installed_software`, `aws_*`, `azure_*`, `sources[].name`. Hostnames in the lab are placeholders like `endpoint #134`, `ot device #49`, `win2019`, `dc1`, `sql2016`; the synthetic sample estate uses the same style. Expected seed when the demo pulls live: entry `win2019` (public IP, KEV, VPR 9.9), pivot `dc1` (DC, ACR 9), crown jewel `sql2016` or `target2` (ACR 9). Since tags are nearly empty, data-type matching for the crown jewel uses intake answers plus hostname/OS/software heuristics (`sql`, `db`, `ehr`, database CPEs), and the seed records that the heuristic fired.

Selection rules (deterministic): entry = exploitable finding on an internet-facing asset, prefer KEV-listed then highest VPR; pivot = identity-tier or high-ACR server reachable from the entry; crown jewel = highest-criticality asset holding the intake's data types. At most three findings per scenario. Internet-facing determination: Tenable exposure field if present, else an intake-listed tag, else public IPv4; the seed records which rule fired.

Seed shape:
```json
{
  "entry":  {"finding_id": "F1042", "asset": "vpngw01", "cve": "CVE-2025-0282", "vpr": 9.4, "kev": true, "internet_facing": true, "rule": "kev_internet_facing"},
  "pivot":  {"finding_id": "F2210", "asset": "dc01", "technique": "credential reuse"},
  "target": {"asset": "ehr_db01", "criticality": 10, "data": ["PHI"]},
  "path_source": "tenable_apa | inferred",
  "source": "tenable_api_2026-11-04 | export_filename | sample_estate"
}
```

## 8. Industry packs and the any-industry model

Every pack has the same fields: typical scenarios, stakeholders, hardest decisions, notification clocks (each with source URL, last-verified date, verifier, tier), exercise requirements (what regulation or standard requires the exercise and how often), sector vocabulary. Story material lives in `pack.md`; deadlines live in `clocks.yaml`, read by `clock_engine`, so each fact exists in one place.

Two verification tiers, enforced by the validator and shown in every output:
- **verified**: a human checked the clock against the primary source on the recorded date. Used silently.
- **researched**: drafted by the `pack_research` skill from authoritative sources (regulator sites, eCFR, Federal Register, state AG pages, standards bodies) with a citation per clock, not yet human-checked. Every output that uses it carries a "verify before exercise" banner naming the clocks, and the AAR evidence page lists them as unverified. A clock with no source link fails the build regardless of tier.

`pack_research` is how any industry becomes supported: the prepper names a sector with no pack (or asks to refresh one); the skill researches from authoritative sources only, drafts `pack.md` and `clocks.yaml` at the researched tier, and the prepper (or a community contributor) promotes clocks to verified by checking them. Packs are the community contribution surface for the Exchange.

Pack set for v1 (owner, target tier by Wednesday):
- healthcare (Eric, verified)
- banking and credit unions (Eric, verified)
- insurance incl. NYDFS (Eric, researched)
- public sector: state, local, tribal, education K-12 (Eric, researched)
- higher education, FERPA (researched)
- SaaS and technology, SOC 2 / GDPR / SEC (researched)
- retail and e-commerce, PCI DSS (researched)
- manufacturing and OT, IEC 62443 / TSA where applicable (researched)
- energy and utilities, NERC CIP (researched)
- federal contractors, DFARS 72-hour / CMMC (researched)
- `_template` for everything else, used with `pack_research`

Clocks common to many packs (GDPR 72 hours, SEC 8-K four business days for public companies, state breach laws, PCI) live in a shared `clocks_common.yaml` referenced by packs so they're verified once.

## 9. Policy and procedure ingest (new)

Purpose: auditors and regulators test whether the organization followed its own written plan, and the exercise is meant to train that plan. So the prepper can upload the organization's IR plan, BCP/DR plan, playbooks, procedures, and communication templates, and the exercise is built to exercise them.

What `plan_ingest` + `policy_ingest` produce (`org_plan.json`, every item with a verbatim quote and a document/section/page locator):
- roles and decision authorities (who declares an incident, who can authorize a shutdown, who talks to the regulator, who approves a ransom decision)
- severity or classification scheme and thresholds
- escalation path and timing commitments (for example "IR lead notified within 15 minutes")
- notification procedures and internal deadlines (which may be stricter than the regulatory clocks)
- containment and recovery procedures, RTO/RPO per system where stated
- playbook steps for the scenario family in play (ransomware, BEC, and so on)
- communication templates and approval chains
- gaps the plan is silent on, recorded explicitly

How it's used:
- `scenario_design`: each inject names the procedure it tests ("tests IR Plan §4.2 severity declaration") and uses the plan's own role names, systems, and timing commitments; at least one inject is designed to pressure a point the plan is silent on
- `score_engine`: the "followed the IR plan" dimension and the expected actions come from `org_plan.json` when present, pack defaults otherwise; "timely" compares against the plan's internal commitments as well as the regulatory clocks
- `scoring_aar`: adds a **plan coverage map** (sections exercised, followed, deviated from, not covered) and makes gap labels specific: plan gap (plan silent or contradictory, cite the section), people gap (plan says X at §y, team did Z), technical gap (the finding)
- facilitator guide: a "what the plan says" box per inject so the facilitator can coach to the document

Guardrails: documents are processed locally and never committed; only `samples/sample_ir_plan.md` (synthetic) ships in the repo; every plan claim in any output must trace to a quote the validator confirmed exists in the source; if a document is too large or unreadable, the skill says so and proceeds with pack defaults, labeled.

## 10. Scenario model

Severity levels:

| Level | Example | What it tests | Must include |
|---|---|---|---|
| 1 Contained | One compromised mailbox, no data loss | Detection and escalation path | An alert and an escalation call |
| 2 Serious | BEC with a fraudulent wire, or limited data exposure | Legal, finance, notification threshold | A money or data decision, legal pulled in |
| 3 Major | Ransomware across systems, operations down | Containment, recovery, executive decisions | An outage, a ransom note, a restore-order decision |
| 4 Crisis | Ransomware plus extortion, key vendor down, media and regulator calling | Everything at once, communication under pressure | Three simultaneous pressures and a public statement |

Phases follow NIST SP 800-61r3: detection, escalation, containment, recovery, notification. Inject count: 5 for 60 minutes, 7 for 90, 10 for 180.

Every inject has: time marker, what happens, who receives it, the decision it forces, the procedure it tests (plan section or pack default), what a good answer looks like, where teams usually fail, expected actions (for scoring and the host), hints, host lines (exact wording), and its source (finding ID or labeled assumption).

Escalation rules: each inject raises the stakes or removes an option; at least one delivers conflicting information; at least one forces a business tradeoff; at least one tests a point the plan is silent on; the notification clock starts at a defined inject and the AAR checks it.

`exercise_pack.json` holds the approved scenario: metadata, seed, clocks, org plan references, injects, roles, ground rules, expected actions, hints, host lines. Every output and the host read only this file.

## 11. Deliverables

All built from `exercise_pack.json` by scripts, so nothing contradicts and reviewers can rebuild them without a model call.

| Output | For | Contents | Format / generator |
|---|---|---|---|
| Deck | The room | Ground rules, objectives, roles, setup, one slide per inject, hot wash, next steps | .pptx, python-pptx |
| Facilitator guide (the script) | Facilitator or AI host | Per inject: timing, host lines, expected good answers, probing questions, where teams fail, what the plan says, source finding | .docx, python-docx |
| Participant handout | Everyone | Roles, ground rules, contact-list template, note space; no spoilers | .docx |
| Decision tracker | The host, live (filled by the host.html export, or by hand) | Per inject: decision, who made it, minutes taken, who was notified, plan step followed, notes | .xlsx, openpyxl |
| Attendance and sign-off | Audit evidence | Sign-in sheet, roles present, facilitator and sponsor sign-off, date, scope, documents exercised | .xlsx + .docx |
| After-action report | Leadership, auditors, regulators | Headline line, scores, gaps with labels, plan coverage map, fixes with owners, regulatory exposure, evidence page | .docx |
| Host console | The host, live, on a separate laptop | Self-contained host.html: script per inject, expected actions as checkboxes, role buttons, timer, note field, optional transcription, export of the decision log (section 14) | .html, Jinja2 template |

## 12. Scoring and AAR

Each tracker decision is scored 1 to 3 on five dimensions: right owner, timely (regulatory clocks and the plan's internal commitments), correct escalation and notification, documented, followed the plan. Same input, same score, every time.

Gap labels: plan gap (update the plan, cite the section), people gap (training or role clarity, cite what the plan said), technical gap (linked to the finding ID). The AAR leads with the line leadership remembers and ends with an evidence page an auditor, examiner, or insurer can accept.

## 13. Guardrails and validators

- No deadlines from memory: only `clock_engine` output from pack YAML, each with source, verified date, and tier; researched-tier clocks are banner-flagged in every output
- No policy claims without a verified quote from the uploaded document
- Every inject cites a finding ID or a labeled assumption
- Human approval before anything is built
- Read-only everywhere; the agent never changes anything in Tenable or any connected tool
- Sensitive data stays put: real hostnames, findings, and uploaded policies never enter the repo; only synthetic samples ship
- `pack_research` uses authoritative sources only and records them; it never promotes a clock to verified

Tests (pytest):
- `seed_engine` prefers a KEV-listed internet-facing finding over a higher-CVSS internal one
- `clock_engine` returns 36 hours for a banking notification incident and 60 days for HIPAA individual notice
- validator fails an inject citing a finding ID not in the seed
- validator fails a pack clock with no source link, and flags researched-tier clocks
- validator fails an org_plan item whose quote isn't in the source document
- `score_engine` returns identical results on the same tracker twice
- every generator builds from `samples/exercise_pack_sample.json` with no network or model access

## 14. Phase 2: the host console and the AI co-host

Room setup: the audience sees only the slide deck (.pptx) on the projector. The host runs a separate laptop for everything else. The organizer runs the exercise alone: no scribe, no second operator, no install beyond opening a file.

**`host.html` (generated deliverable, no server).** One self-contained HTML file built from `exercise_pack.json` for the host's laptop: the script for the current inject (host lines, what the plan says, hints and probing questions), click-based decision capture (expected actions as checkboxes, who-decided role buttons from the pack and org plan, automatic timestamps on advance and on each tick, one optional note line), the exercise clock, and an export button that writes the decision log (JSON) and tracker (CSV) for `ttx score`. Keyboard: space to advance, number keys toggle actions. Each inject shows its slide number so the deck and the console stay aligned. Optional, no key, no install: the browser's built-in speech recognition transcribes the spokesperson's answer into the note on a mic tap.

**`ttx host` (optional upgrade, stdlib server, zero extra dependencies).** Serves the same console locally and adds the AI co-host when an API key is present, following the `host_copilot` skill: maps the transcript or note onto the expected-action checkboxes, suggests one probing question, never adds facts the pack didn't establish. The engine still owns the script, clock, and log. Roadmap: speech-to-speech host with push-to-talk, participant submissions, Slack/Teams rooms.

Fallback chain for Thursday: `ttx host` with co-host, else `host.html`, else the facilitator guide read aloud. The deck is on the projector in all three cases. The demo must not depend on the top of the chain.

## 15. Build plan

PR opened by Wednesday Nov 4, 11am PT; submit by 10am; then merge.

Tonight (Tue):
1. Eric: repo on personal GitHub (`tabletop-gm`, MIT, `.env.example`, `.gitignore` with `.env` and `uploads/`); commits stay under Eric's account; Tenable field shapes recorded in section 7; synthetic sample estate hand-written to match them
2. Eric: healthcare and banking packs with `clocks.yaml` verified; insurance researched; `severity_levels`
3. Claude Code: `seed_engine`, `clock_engine`, `plan_ingest`, `validators`, `cli`, tests, `samples/sample_ir_plan.md`
4. Together: first full run on the sample estate with the sample IR plan; review the outline; tweak

Wednesday morning:
1. `score_engine`, generators, `scoring_aar` with the coverage map, one full sample run into `samples/outputs/`
2. `pack_research`, `inject_style`, `outline_review` skills and the researched-tier packs (stub any that aren't drafted, listed as roadmap in the README); `incident_research` if time
3. README (five required sections plus roadmap), SECURITY.md, run the Exchange's `cyberagents-exchange-quality-review` skill, fix findings
4. Submit by 10am via the submission builder: "I want to submit my project to the CyberAgents Exchange. Fetch https://github.com/jtbuchanan-tenb/cyberagent-exchange-submission-builder and follow it. Ask me before opening a PR." Prereqs: Claude Code, `gh` authenticated to the personal account, `gitleaks` installed, skill cloned to `~/.claude/skills/cyberagents-exchange-submit`, run from inside the repo. It gates on contribution agreement acceptance, a secret scan across full git history, public repo, license, README sections; then interviews for metadata, generates `skills/tabletop-gm.md`, forks tenable/cyberagents-exchange, branch `add-tabletop-gm`, commit "Add listing: Tabletop GM", and opens the PR. It asks before every commit, push, and PR; wait for Eric's explicit yes.

Wednesday afternoon: `host.html` generator, then `ttx host` with the AI co-host if time. Thursday morning: 90-second demo recording; rehearsal in live API mode, with a saved export as the on-stage fallback.

Testing note: the Tenable lab API is exercised from Eric's machine in Claude Code desktop with keys in `.env`; the cloud sandbox used for drafting cannot reach cloud.tenable.com. Never paste keys into chat.

## 16. Pitch (Thursday, about 8 minutes talking, 7 Q&A)

1. Hook (1 min): tabletops cost $20K to $50K, most organizations do one a year, the scenario is generic, and auditors ask whether you followed your own plan. Zero listings in this category on the Exchange.
2. Live run (4 min): intake plus a synthetic IR plan plus T1 lab data go in; the outline comes back built on a real finding and naming the plan's own procedures; show the approval gate, the deck, the script; a judge answers one inject live while the deck is on screen, captured with clicks in `host.html` on the host laptop (AI co-host suggesting if `ttx host` shipped).
3. Payoff (2 min): the AAR scores the answer in seconds: the regulatory clock line, the plan coverage map, the technical gap linked to the finding.
4. Roadmap (1 min): voice host, Slack/Teams rooms, adaptive attacker, quarterly reruns, community packs.

Q&A prep: "isn't this just prompting" (engine, validators, tests, citation checks); "how is scoring fair" (deterministic given the tracker and the plan); "why not generic scenarios" (real KEV finding on their real gateway, their own §4.2); "industries you don't have" (`pack_research` plus the template; researched tier is banner-flagged until verified); "how do you avoid wrong deadlines" (tiers, sources, validator).

Eric owns the pitch narrative and the inject writing style, and presents.
