# SaaS and technology companies pack

Tier: researched (per-clock tiers live in `clocks.yaml`)
Last reviewed: 2026-11-03
Owner: unassigned

Story material for software-as-a-service and technology companies lives here; every deadline lives in `clocks.yaml`; scoring defaults live in `defaults.yaml`. Drafted by the `pack_research` skill from the sources listed at the end and not yet human-checked.

## Who this pack is for

Multi-tenant SaaS vendors, developer platforms, managed service providers, and technology companies whose product their customers run their business on, from a 50-person startup with one production cloud account to a 5,000-person public company with regional deployments. They hold customer data on behalf of thousands of organizations, so one incident becomes many customers' incidents. The bodies that matter are the AICPA (SOC 2 through the Trust Services Criteria), EU member-state CSIRTs and competent authorities under NIS2, financial supervisors under DORA when the company serves banks, insurers, or investment firms, the UK Information Commissioner under the NIS Regulations for relevant digital service providers, CERT-In for operations in India, the Australian OAIC, EU data protection authorities under GDPR, the SEC for public companies, and US state attorneys general. GDPR, SEC Form 8-K, state breach laws, and CIRCIA are shared across packs and come from `clocks_common.yaml`.

## Typical scenarios

- Credential theft against the customer admin console: a support engineer's session token is replayed to read tenant configuration across accounts, raising the question of which customers were touched and when to tell them.
- Compromise of the CI/CD pipeline or a build dependency: a tampered package reaches production, so the incident is also a product recall and every customer on the release needs a notice.
- Ransomware and extortion in the production cloud account: object storage encrypted, snapshots deleted, and a threat to publish customer data.
- Leaked API keys in a public repository: automated scanners find them within minutes and the team must decide whether to rotate keys that would break customer integrations.
- Orphaned access by a departed contractor: a service account keeps pulling customer exports after offboarding, discovered only by a customer's own audit.
- Sub-processor breach: a downstream analytics or email vendor is compromised and the company must notify its own customers about data it never directly lost.

## Stakeholders and roles

CEO; CISO or Head of Security; CTO or VP Engineering (owns the change freeze, rollback, and the kill switch); Head of Security Operations as incident commander; Platform or Site Reliability Lead; VP Customer Success (customer notices, executive escalations, status page); Trust and Compliance Lead (SOC 2 auditor liaison, customer questionnaires, attestations and bridge letters); General Counsel; Data Protection Officer; Head of Communications; CFO (revenue at risk, SLA credits, insurance).

Outside the building: the cloud provider's account team, sub-processors, outside counsel and forensics, the SOC 2 auditor, and the cyber insurer.

## Hardest decisions

1. Tell customers now or wait for facts: enterprise contracts promise notice within 24 to 72 hours of a confirmed breach, but confirmation rarely arrives that early; a vague notice triggers hundreds of security questionnaires, a late one breaches the contract.
2. Rotate every customer-facing key and token: it ends the attacker's access and also breaks every customer integration at once, during the customers' business hours.
3. Take the product down: a full outage protects data and starts SLA credit clocks and churn conversations; a partial degradation may leave the attacker inside.
4. Who speaks to the regulators: one incident can touch CSIRTs in several member states, the ICO, CERT-In, the OAIC, and the customers' financial supervisors under DORA, each with a different form and clock, while the DPO, the CISO, and outside counsel each think they own it.
5. Pay the extortion demand: payment may be unlawful depending on the actor, is not covered by every policy, and does not stop publication; refusing means customer data appears on a leak site with the company's name on it.

## Notification clocks

`clocks.yaml` is the source of truth; this is a summary. GDPR (72 hours to the supervisory authority), SEC Form 8-K Item 1.05 for public companies, US state breach laws, and CIRCIA come from `clocks_common.yaml`. PCI card brand conventions, where the company stores or processes card data, also come from the common file rather than this pack.

Customer contractual notice windows (commonly 24, 48, or 72 hours after confirmation, sometimes "without undue delay") are not law and vary by contract, so they are described here rather than coded as clocks: read the master services agreement and data processing addendum during intake, pick the tightest window among the top customers, and add it to the timeline as a labeled assumption. SOC 2 has no notification deadline; it is an exercise requirement, listed in the next section.

| Clock id | Goes to | Deadline | Tier |
|---|---|---|---|
| `saas_nis2_art23_early_warning` | member-state CSIRT or competent authority | 24 hours from awareness of a significant incident | researched |
| `saas_nis2_art23_incident_notification` | member-state CSIRT or competent authority | 72 hours from awareness | researched |
| `saas_nis2_art23_final_report` | member-state CSIRT or competent authority | one month after the incident notification | researched |
| `saas_dora_art19_initial_notification` | the financial-entity customer's competent authority, filed by the customer with the provider's facts | 4 hours from classification as major, no later than 24 hours from awareness | researched |
| `saas_dora_art19_intermediate_report` | same | 72 hours from the initial notification | researched |
| `saas_dora_art19_final_report` | same | one month after the intermediate report | researched |
| `saas_uk_nis_rdsp_incident_notice` | UK Information Commissioner | 72 hours from first awareness, RDSPs only | researched |
| `saas_certin_incident_report` | CERT-In | 6 hours from noticing the incident | researched |
| `saas_oaic_ndb_assessment` | internal, enforced by the OAIC | 30 calendar days to complete the assessment | researched |
| `saas_oaic_ndb_commissioner_statement` | Australian Information Commissioner, then affected individuals | as soon as practicable (no fixed hours) | researched |

Flags used: `nis2_essential_or_important_entity`, `dora_in_scope` (the company serves EU financial entities under DORA contracts), `uk_nis_rdsp` (online marketplace, search engine, or cloud computing service above the UK small-enterprise threshold).

Intake prompts that decide which clocks fire:

- In which EU member state is the company established, and has it been identified as an essential or important entity (sets the NIS2 flag and the receiving CSIRT)?
- Do any customers fall under DORA, and what does their contract say about incident facts and timing (sets `dora_in_scope`)?
- Does the company run a UK online marketplace, search engine, or cloud service above the small-enterprise threshold (sets `uk_nis_rdsp`)?
- Does it operate or hold data in India or Australia (CERT-In and OAIC clocks)?
- What is the tightest contractual notice window among the top ten customers (recorded as a labeled assumption, not a clock)?

## Exercise requirements

- SOC 2 Trust Services Criteria, CC7 System Operations: no notification clock, but the incident response program and its periodic evaluation are what the auditor tests, and a documented tabletop is the usual evidence (`saas_soc2_tsc_incident_response_evaluation` in `clocks.yaml`; the criteria PDF itself could not be fetched, so the criterion numbers must be checked before use).
- Enterprise customer contracts, security questionnaires, and cyber insurance applications routinely ask whether the plan was tested in the last 12 months; these are conventions, not coded.
- NIS2 Article 21 risk-management measures and DORA's resilience testing chapters were not read for this draft and are not coded; a verifier may add them.

## Sector vocabulary

Tenant, multi-tenant, control plane, data plane, production account, blast radius, status page, SLA, SLA credit, MSA, DPA, sub-processor, SOC 2 Type II, bridge letter, trust center, security questionnaire, feature flag, kill switch, rollback, change freeze, IAM role, service account, secrets manager, key rotation, session token, identity provider.

CI/CD, build pipeline, artifact registry, SBOM, infrastructure as code, on-call, pager, sev1, incident channel, postmortem, root cause analysis, customer-facing RCA, data subject access request, breach of contract notice, early warning, significant incident, major ICT-related incident, relevant digital service provider, eligible data breach.

## Sources

- https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022L2555 (read 2026-11-03; NIS2 Article 23(1), (3), (4) and Annexes I and II)
- https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022R2554 (read 2026-11-03; DORA Articles 19 and 20)
- https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32025R0301 (read 2026-11-03; Commission Delegated Regulation (EU) 2025/301, Article 5)
- https://www.legislation.gov.uk/uksi/2018/506/regulation/12 (read 2026-11-03; RDSP duty, 72 hours)
- https://www.legislation.gov.uk/uksi/2018/506/regulation/11 (read 2026-11-03; OES duty, 72 hours, not coded for this pack)
- https://www.cert-in.org.in/Directions70B.jsp (read 2026-11-03; directions index page)
- https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf (read 2026-11-03; directions (ii) and (iv))
- https://www.oaic.gov.au/privacy/notifiable-data-breaches/preventing-preparing-for-and-responding-to-data-breaches/data-breach-preparation-and-response/part-4-notifiable-data-breach-ndb-scheme (read 2026-11-03; s 26WH, 26WK, 26WL)
- https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services (read 2026-11-03; SOC suite overview, 2027 exposure drafts)
- https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022 (read 2026-11-03; download page only, criteria PDF not fetched)
