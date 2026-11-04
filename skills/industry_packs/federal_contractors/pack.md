# Federal and defense contractors pack

Tier: researched (per-clock tiers live in `clocks.yaml`; promote after a human check)
Last reviewed: 2026-11-03
Owner: unassigned

Story material lives here; every deadline lives in `clocks.yaml`; scoring defaults live in `defaults.yaml`. Drafted by the `pack_research` skill from primary sources on 2026-11-03 and not yet human-checked.

## Who this pack is for

Defense industrial base companies and other federal contractors that process, store, or transmit Controlled Unclassified Information (CUI) or Federal Contract Information on their own systems, operate systems on behalf of an agency, or deliver cloud services under a FedRAMP authorization. It fits organizations from a 40-person machine shop with a single DFARS 252.204-7012 contract to a multi-division prime with cleared facilities and a FedRAMP High offering. The regulators and standards bodies that matter: the Department of Defense (DFARS 252.204-7012, the CMMC Program at 32 CFR Part 170, DoD Cyber Crime Center and DIBNet), the FAR Council (FAR 52.204-21 and the proposed FAR CUI rule), NIST (SP 800-171 Rev 2 and Rev 3), the FedRAMP PMO at GSA and the agency authorizing officials, CISA (Federal Incident Notification Guidelines), DCSA for cleared facilities, and the SEC for public companies. Set the intake flags `defense_contractor`, `fedramp_csp`, or `operates_federal_system` so the right clocks load, and mark the data type `CUI` when it is in scope.

## Typical scenarios

- Compromise of an internet-facing remote access gateway with a known exploited vulnerability, followed by credential theft and access to the file shares and engineering data environment that hold CUI. The scenario tests whether the 72 hour DIBNet clock starts at discovery and whether anyone can find the medium assurance certificate.
- Ransomware across the corporate network that encrypts the ERP and the program management systems supporting several contracts, forcing a delivery impact conversation with contracting officers while the forensic team cannot yet say whether CUI was taken.
- Subcontractor incident: a machining or software subcontractor reports that drawings it holds were accessed, and the prime must decide what it reports to DoD and to the customer without owning the evidence.
- Cloud service incident for a FedRAMP-authorized offering: a misconfiguration or an account takeover exposes agency tenant data, with a one hour report to FedRAMP and agency points of contact and a separate CISA report if the attack vector matches CISA's taxonomy.
- Insider or spillage event in a cleared facility where classified or export-controlled data lands on an unclassified system, pulling the Facility Security Officer and DCSA into a cyber incident.
- Business email compromise against the contracts or accounts receivable team that redirects a government payment or leaks proposal data.

## Stakeholders and roles

Security and compliance:
- Incident Response Lead (incident commander)
- Chief Information Security Officer and Chief Information Officer
- Information System Security Manager or CUI Program Manager (owns the system security plan)
- Facility Security Officer and Insider Threat Program Senior Official (cleared facilities)
- Export Control Officer (ITAR and EAR data)

Contracts, programs, and legal:
- Contracts Manager and the contracting officers and CORs for each affected contract
- Program Managers for the affected programs
- General Counsel and outside counsel (privilege, False Claims Act exposure, notification obligations)

Executive and external:
- Chief Executive, Chief Financial Officer, and the board
- Communications Lead
- FedRAMP authorizing officials and agency ISSOs (cloud offerings); agency incident response teams for contractor-operated systems
- Prime contractor or affected subcontractors under the flowdown clause
- DoD Cyber Crime Center (DIBNet), DCSA, the FBI, the cyber insurance carrier
- C3PAO or registered practitioner organization that supports the CMMC assessment

## Hardest decisions

- When discovery happened: the DFARS clock runs from discovery of a cyber incident, not from confirmation that CUI was affected. Teams argue about whether an alert was an incident and lose a day; the regulator will read the timeline backward from the ticket.
- Reporting with incomplete facts: the DIBNet report asks for affected contracts, CUI categories, and the attack vector. Filing early with gaps and updating is the compliant path; waiting for certainty is the common failure.
- Rebuild versus preserve: engineering wants the file server back; the clause requires preserved images and packet capture for at least 90 days from the report, and DoD may ask for the media. Who stops the rebuild?
- Telling the customer: contracting officers and program customers often hear about an incident from the news or from DoD before the contractor calls. Who calls, in what order, and what is said about delivery impact?
- Flowdown: a prime deciding whether a subcontractor's incident is its own reportable incident, and a subcontractor deciding whether to report to DoD directly, to the prime, or both. The clause says both.
- Public company disclosure: a material incident on a defense program adds the SEC Form 8-K four business day clock on top of the DoD report, and the two audiences need different levels of detail.

## Notification clocks

`clocks.yaml` is the source of truth. GDPR, SEC Form 8-K, state breach laws, and CIRCIA come from `clocks_common.yaml` and load when `includes_common: true`. Summary of the pack's own clocks:

| id | Goes to | Deadline | Tier |
|---|---|---|---|
| dfars_7012_rapid_report_72h | DoD via DIBNet (and the prime, for subcontractors) | 72 hours from discovery of any cyber incident | researched |
| dfars_7012_media_preservation_90_days | Retention obligation (DoD may request the media) | at least 90 days from submission of the cyber incident report | researched |
| cmmc_level2_incident_reporting | Designated officials and authorities named in the organization's plan | no deadline in 32 CFR Part 170; Level 2 incorporates NIST SP 800-171 Rev 2 3.6.2 | researched |
| nist_800_171_3_6_2_incident_reporting | Organization-defined authorities | organization-defined time period (Rev 3), no number in Rev 2 | researched |
| fedramp_csp_incident_one_hour | FedRAMP, CISA, agency points of contact, impacted customers | 1 hour from identification (legacy procedures); tiered 15 minutes to 1 business day under the Consolidated Rules for 2026 | researched |
| cisa_federal_incident_notification_one_hour | CISA | 1 hour from identification; binds agencies and reaches contractors by contract | researched |

FAR 52.204-21 has no reporting clock; its fifteen safeguarding requirements include "identify, report, and correct information and information system flaws in a timely manner" with no recipient or deadline. The proposed FAR CUI rule is a note only: the January 2025 proposal would have required an 8 hour report and the June 2026 superseding proposal under the Revolutionary FAR Overhaul proposes 72 hours; neither is in force as of 2026-11-03.

## Exercise requirements

- NIST SP 800-171 Rev 2 requirement 3.6.3: test the organizational incident response capability; Rev 3 requirement 03.06.03 adds an organization-defined frequency and names tabletop exercises as an acceptable test (`nist_800_171_3_6_3_test_ir`).
- CMMC Level 2 practice IR.L2-3.6.3, which 32 CFR 170.14(c)(3) makes identical to NIST SP 800-171 Rev 2 3.6.3; a dated tabletop record is the evidence an assessor expects (`cmmc_ir_l2_3_6_3`).
- FedRAMP continuous monitoring expects incident response testing under the IR control family of the authorized baseline; not drafted as a requirement here and should be added when the pack is human-checked.
- Contract-specific exercise clauses (for example agency incident response plan testing for contractor-operated systems) vary by contract and should be read from the contract during intake.

## Sector vocabulary

Clause and regulation terms (use them exactly, the contracts manager will):
- CUI and CUI categories (CTI, export controlled, privacy), Federal Contract Information, covered defense information, covered contractor information system
- Cyber incident, compromise, rapid report, operationally critical support, flowdown, prime and subcontractor, contracting officer, COR
- DFARS 252.204-7012, 7019, 7020, and 7021; SPRS score; system security plan (SSP); plan of action and milestones (POA&M)
- CMMC Level 1, 2, and 3; C3PAO; self-assessment; affirmation; NIST SP 800-171 and 800-171A; Rev 2 and Rev 3
- FedRAMP authorization, Rev 5 and 20x, agency authorizing official, ISSO, PAIN rating, Class A to D, trust center

Reporting and security terms (use them so the injects sound like the organization's own incident):
- DIBNet, DC3 (DoD Cyber Crime Center), medium assurance certificate, incident collection form, malware submission
- Federal Incident Notification Guidelines, attack vector taxonomy, functional impact, information impact, recoverability
- Facility Security Officer, DCSA, spillage, ITAR and EAR, cleared facility, NISPOM, insider threat program
- Engineering data environment, PLM system, drawing vault, program share, government-furnished information

## Sources

- https://www.ecfr.gov/current/title-48/chapter-2/subchapter-H/part-252/subpart-252.2/section-252.204-7012 (DFARS 252.204-7012; eCFR blocks automated fetches, text confirmed at https://www.law.cornell.edu/cfr/text/48/252.204-7012), read 2026-11-03
- https://www.ecfr.gov/current/title-48/chapter-1/subchapter-H/part-52/subpart-52.2/section-52.204-21 (FAR 52.204-21; text confirmed at https://www.law.cornell.edu/cfr/text/48/52.204-21, no reporting clock), read 2026-11-03
- https://www.ecfr.gov/current/title-32/subtitle-A/chapter-I/subchapter-D/part-170 (CMMC Program; text confirmed at https://www.law.cornell.edu/cfr/text/32/170.14 and https://www.law.cornell.edu/cfr/text/32/170.3), read 2026-11-03
- https://csrc.nist.gov/pubs/sp/800/171/r3/final (NIST SP 800-171 Rev 3 publication page; requirement text from https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171r3.pdf and https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171r2.pdf), read 2026-11-03
- https://fedramp.gov/legacy/playbook/csp/continuous-monitoring/incident-communication/ (FedRAMP legacy incident communications procedures, one hour), read 2026-11-03
- https://fedramp.gov/2026/reference/incident-evaluation-and-communication/ (FedRAMP Consolidated Rules for 2026, tiered initial report deadlines), read 2026-11-03
- https://www.cisa.gov/federal-incident-notification-guidelines (CISA Federal Incident Notification Guidelines, one hour), read 2026-11-03
- https://www.govinfo.gov/content/pkg/FR-2025-01-15/html/2024-30437.htm (proposed FAR CUI rule, 90 FR 4278, 8 hour report proposal, superseded), read 2026-11-03
- https://www.govinfo.gov/content/pkg/FR-2026-06-23/html/2026-12559.htm (Revolutionary FAR Overhaul proposed rule, 91 FR 37550, proposed FAR 52.240-7 with 72 hour report), read 2026-11-03
- https://www.law.cornell.edu/uscode/text/6/681b (CIRCIA statute, used by clocks_common.yaml), read 2026-11-03
