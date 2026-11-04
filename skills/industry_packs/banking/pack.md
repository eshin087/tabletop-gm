# Banks and credit unions pack

Tier: researched (per-clock tiers live in `clocks.yaml`; promote after a human check)
Last reviewed: 2026-11-03
Owner: unassigned (drafted by Claude Code; human verification pending)

Story material lives here; every deadline lives in `clocks.yaml`; scoring defaults live in `defaults.yaml`.

## Who this pack is for

Community banks, regional banks, federal and state savings associations, bank holding companies, and federally insured credit unions, from a single-branch institution to a multi-state regional. Also covers the non-bank financial institutions under FTC jurisdiction (mortgage lenders, finance companies) through the `nonbank_financial_institution` flag. The regulators and standards that matter: the OCC, Federal Reserve, and FDIC (joint computer-security incident notification rule and the Interagency Guidelines), the NCUA for credit unions, FinCEN (suspicious activity reporting), state banking departments, the NYDFS for New York licensees (clock in the insurance pack), the FFIEC IT Examination Handbook, the FTC Safeguards Rule for non-banks, and card network rules for issuers. Set the supervisor flag that matches the charter: `occ_supervised`, `frb_supervised`, `fdic_supervised`, or `credit_union`, plus `bank_federally_insured` for any insured depository.

## Typical scenarios

- Ransomware that reaches the core banking platform or the systems feeding it, taking digital banking, wires, and branch teller systems down together and forcing the 36-hour determination question.
- Business email compromise ending in a fraudulent wire or ACH batch, where the first signal is a customer or a correspondent bank calling, not an alert.
- Core processor or critical service provider incident: the provider's four-hour disruption notice arrives and the bank must decide whether it now has a notification incident of its own.
- Credential stuffing and account takeover against online banking, with customer losses accumulating while the team debates shutting the channel.
- Compromise of an internet-facing edge device (VPN, remote access, or file transfer appliance) with a known exploited vulnerability, followed by movement toward the domain and the core interfaces.

## Stakeholders and roles

Incident Commander, Chief Information Security Officer, Chief Information Officer, Chief Risk Officer, BSA/AML Officer, Chief Compliance Officer, General Counsel and outside breach counsel, Head of Operations and Treasury (wires, ACH, cash), Head of Retail and Digital Banking, Director of Communications, Chief Executive Officer, Chief Financial Officer, Third-Party Risk Manager, the board risk committee chair, the core processor's incident contact, the cyber insurance carrier, and the primary federal regulator's examiner-in-charge.

## Hardest decisions

- Determination: the 36-hour (banks) or 72-hour (credit unions) clock starts when the organization determines a notification incident has occurred. Teams either never name the moment or name it too late, and the examiner asks for the timestamp.
- Suspending payment rails: stopping wires and ACH protects the institution and its customers, and it also strands payrolls and closings. Who approves it, and what is the customer message?
- Shutting digital banking: taking online and mobile banking down stops account takeover and also sends every customer to the branch and the call center on the same morning.
- The core processor's status: the bank depends on a provider it does not control; the decision is whether to fail over, wait, or activate manual branch procedures.
- Customer notice and the SAR: the Interagency Guidance says "as soon as possible" and FinCEN says 30 days; both have owners who are rarely in the room for a cyber exercise.
- Paying a ransom: sanctions screening, insurer consent, and board notification all sit on the chief executive's desk at once.

## Notification clocks

`clocks.yaml` is the source of truth. Summary:

| id | Goes to | Deadline | Tier |
|---|---|---|---|
| occ_notification_incident_36h | OCC | 36 hours from determination | researched |
| frb_notification_incident_36h | Federal Reserve | 36 hours from determination | researched |
| fdic_notification_incident_36h | FDIC | 36 hours from determination | researched |
| bank_service_provider_notice | Service provider to bank customers | As soon as possible after a 4-hour disruption determination | researched |
| ncua_reportable_cyber_incident_72h | NCUA | 72 hours from reasonable belief | researched |
| glba_interagency_customer_notice | Primary federal regulator and affected customers | As soon as possible | researched |
| fincen_sar_30_days | FinCEN | 30 calendar days from initial detection (60 maximum) | researched |
| ftc_safeguards_nonbank_30_days | FTC (non-bank institutions, 500 or more consumers) | 30 days from discovery | researched |

NYDFS 23 NYCRR 500.17 (72 hours) loads from the insurance pack when the intake sets `nydfs_licensed`. GDPR, SEC Form 8-K for public holding companies, state breach notification laws, and CIRCIA come from `clocks_common.yaml`.

## Exercise requirements

- FFIEC IT Examination Handbook, Business Continuity Management booklet: an enterprise-wide testing program with exercises and tests, including cyber events, with results reported to the board. Examiners expect at least annual exercises and look for cyber scenarios.
- FTC Safeguards Rule, 16 CFR 314.4(h): a written incident response plan for non-bank financial institutions.
- The Interagency Guidelines Establishing Information Security Standards require a response program; the exercise is the evidence that it works.

## Sector vocabulary

Notification incident, determination, covered services, core processor, core banking platform, digital banking, online banking, mobile banking, wire room, ACH origination, correspondent bank, Fedwire, FedLine, cash positioning, branch manual procedures, teller platform, item processing, card processor, card networks, BIN, BSA Officer, SAR (suspicious activity report), FinCEN, FS-ISAC, examiner-in-charge, matters requiring attention, board risk committee, third-party risk management, business continuity plan, recovery time objective.

## Sources

- https://www.law.cornell.edu/cfr/text/12/53.3 (read 2026-11-03; mirror of eCFR 12 CFR Part 53)
- https://www.law.cornell.edu/cfr/text/12/53.4 (read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/12/225.302 (read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/12/304.23 (read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/12/748.1 (read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/12/appendix-B_to_part_30 (read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/31/1020.320 (read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/16/314.4 (read 2026-11-03)
- https://ithandbook.ffiec.gov/it-booklets/business-continuity-management/ (not fetched 2026-11-03; verify by hand)
