# Insurance carriers and producers industry pack

Tier: researched (per-clock tiers live in `clocks.yaml`)
Last reviewed: 2026-11-03
Owner: unassigned

This pack covers property and casualty carriers, life and annuity carriers, and the agencies and producers that distribute for them. Story material lives here; every deadline lives in `clocks.yaml`; scoring defaults live in `defaults.yaml`. Health insurers and HMOs load this pack and the healthcare pack together, because their HIPAA clocks (45 CFR 164.400 to 164.414) live in the healthcare pack and are not duplicated here.

## Who this pack is for

Insurers, reinsurers, managing general agents, third-party administrators, and licensed producers ranging from a regional mutual with a few hundred staff to a multi-state carrier. The regulators that matter are the state insurance commissioner of the state of domicile (and every state where the licensee holds a license), the New York State Department of Financial Services for anyone licensed under the Banking, Insurance, or Financial Services Law, and state attorneys general under state breach laws. The standards bodies are the NAIC, whose Insurance Data Security Model Law (MDL-668) has been enacted in 28 jurisdictions as of October 2026, and the NYDFS cybersecurity regulation (23 NYCRR Part 500), which the NAIC model was drafted to track.

## Typical scenarios

- Ransomware across claims systems: claims cannot be adjudicated or paid, first-notice-of-loss queues back up, and the extortion payment clocks start the moment anyone pays.
- Business email compromise against premium payments: a spoofed carrier or agency instruction reroutes premium or commission payments, and the loss is discovered at reconciliation.
- Producer portal credential compromise: stolen agent logins are used to pull policyholder data and bind fraudulent policies, which raises binding-authority and consumer notification questions at once.
- Third-party administrator breach: a TPA or claims vendor reports an incident involving the carrier's claimants, and the carrier must decide whether its own 72-hour clocks have started.
- Policy administration platform outage from a vendor incident: a hosted core system is unavailable for days, and the question is operational resilience and BCDR rather than data loss.

## Stakeholders and roles

At the table (titles as the sector uses them):

- Chief Executive Officer: owns the ransom decision and any decision to stop writing or paying.
- Chief Information Security Officer: makes the cybersecurity incident determination that starts the regulator clocks.
- Chief Information Officer: owns system shutdown and the restore order for core platforms.
- General Counsel: owns notification obligations, privilege, and law enforcement contact.
- Chief Compliance Officer: owns regulatory filings and market conduct exposure.
- Chief Privacy Officer: scopes consumer notification across states.
- Chief Claims Officer: decides manual claims workarounds and payment priority.
- Chief Underwriting Officer: decides whether to suspend binding authority.
- Head of Agency and Producer Distribution: owns the producer portal and producer notification.
- Chief Financial Officer and Treasurer: owns premium rerouting and any ransom funding.
- Head of Corporate Communications: owns public statements and policyholder messaging.
- Incident Commander from security operations: runs the technical response.

Outside the building: outside breach counsel, the cyber carrier and its panel forensics firm, sanctions counsel for OFAC screening, reinsurance partners, third-party administrators, and the producers of record.

## Hardest decisions

- When has a "cybersecurity incident" been determined? The NYDFS 72-hour clock and the commissioner clock both run from a determination, so teams either declare too early and over-report or delay the determination and miss the window.
- Whether to pay an extortion demand. Payment starts a 24-hour notice and a 30-day written explanation that must show OFAC diligence and the alternatives considered. The explanation is impossible to write honestly if the diligence was not done before the payment.
- Whether a vendor or TPA incident is the carrier's incident. The NYDFS rule covers incidents at affiliates and third-party service providers, so "it is the vendor's problem" is not a safe answer.
- Suspending binding authority or claims payments. Stopping the business protects data but creates policyholder harm and market conduct exposure; continuing it may extend the compromise.
- Telling producers of record. The NAIC model expects insurers to notify producers of record of affected consumers as directed by the commissioner, which agencies experience as the carrier blaming them.

## Notification clocks

Summary only; `clocks.yaml` is the source of truth. GDPR, SEC Form 8-K, state breach laws, and CIRCIA come from `clocks_common.yaml` and are not repeated here.

| Clock id | Goes to | Deadline | Tier |
| --- | --- | --- | --- |
| `nydfs_500_17_incident_notice` | NYDFS superintendent | 72 hours after determination (flag `nydfs_licensed`) | researched |
| `nydfs_500_17_extortion_payment_notice` | NYDFS superintendent | 24 hours after an extortion payment (flag `nydfs_licensed`) | researched |
| `nydfs_500_17_extortion_payment_explanation` | NYDFS superintendent | 30 days after an extortion payment, written explanation (flag `nydfs_licensed`) | researched |
| `naic_668_commissioner_notice` | Insurance commissioner of the state of domicile or home state | 72 hours after determination, in the 28 jurisdictions that enacted MDL-668 (flag `insurer_licensed`) | researched |

HIPAA breach notification clocks for health insurers are loaded from the healthcare pack. State breach law clocks for policyholder notice and attorney general notice come from the common file.

## Exercise requirements

- 23 NYCRR 500.16(d): each covered entity shall periodically, but at a minimum annually, test its incident response and BCDR plans with all staff and management critical to the response, and its ability to restore critical data and systems from backups. Recorded as `nydfs_500_16_d_annual_plan_test`.
- NAIC MDL-668 Section 4.H: each licensee shall establish a written incident response plan covering roles, decision authority, communications, remediation, documentation, and post-event revision. The model does not state a test interval. Recorded as `naic_668_section_4h_incident_response_plan`.
- Cyber insurance carriers commonly ask for evidence of an annual tabletop at renewal; treat that as a contractual expectation, not a regulation, and confirm it against the policy wording.

## Sector vocabulary

Regulatory terms:

- Covered entity (NYDFS) and licensee (NAIC model): the regulated organization.
- Nonpublic information: the data class both regimes protect.
- Cybersecurity event versus cybersecurity incident: the event is the occurrence; the incident is the reportable subset, and its determination starts the clock.
- Superintendent (NYDFS) and commissioner (state of domicile or home state): the recipients of notice.
- Extortion payment, OFAC diligence, and the 30-day written explanation.
- Certification of material compliance: the April 15 annual filing signed by the highest-ranking executive and the CISO.

Operational terms:

- First notice of loss (FNOL), claims adjudication, claims payment release, reserve.
- Policy administration system, billing and premium intake, premium finance, commission statement.
- Binding authority, quote moratorium, producer of record, producer portal.
- Managing general agent (MGA), third-party administrator (TPA), claims vendor.
- Ceding insurer, assuming insurer, reinsurance treaty, bordereau.
- Market conduct examination, BCDR plan, restore from backups.

## Sources

- https://www.dfs.ny.gov/cybersecurity/23-NYCRR-Part-500 (DFS PDF of the Second Amendment to 23 NYCRR 500; sections 500.16(d) and 500.17(a), (c); read 2026-11-03)
- https://www.dfs.ny.gov/industry_guidance/cybersecurity (DFS cybersecurity landing page with the incident submission link; read 2026-11-03)
- https://content.naic.org/sites/default/files/model-law-668.pdf (NAIC Insurance Data Security Model Law, Sections 4.H and 6; read 2026-11-03)
- https://content.naic.org/sites/default/files/government-affairs-brief-data-security-model-law.pdf (NAIC Government Affairs brief, October 2026, list of 28 implementing jurisdictions; read 2026-11-03)
- https://content.naic.org/sites/default/files/model-law-state-page-668.pdf (NAIC state page for Model 668, Summer 2026, state-by-state citations; read 2026-11-03)
- https://content.naic.org/sites/default/files/legal-adoption-map-668-idsm.pdf (NAIC adoption map, status as of November 3, 2026; the map itself is an image and was not machine-readable; read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/45/164.408 (HIPAA notice to the Secretary, by reference only; read 2026-11-03)
