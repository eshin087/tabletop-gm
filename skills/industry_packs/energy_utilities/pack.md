# Energy and utilities pack

Tier: researched (per-clock tiers live in `clocks.yaml`; promote after a human check)
Last reviewed: 2026-11-03
Owner: unassigned

Story material lives here; every deadline lives in `clocks.yaml`; scoring defaults live in `defaults.yaml`. Drafted by the `pack_research` skill from primary sources on 2026-11-03 and not yet human-checked.

## Who this pack is for

Electric utilities (investor-owned, municipal, cooperative, and federal), generation owners and operators, transmission and distribution operators, balancing authorities and reliability coordinators, natural gas and hazardous liquid pipeline operators, LNG facilities, and drinking water and wastewater utilities. It fits organizations from a 300 MW municipal system with a two-person security team to a multi-state holding company with a 24x7 security operations center. The regulators and standards bodies that matter: NERC and its Regional Entities (CIP standards, approved by FERC), the E-ISAC, the US Department of Energy (Form DOE-417, also called OE-417), CISA, TSA Surface Operations (pipeline security directives), the EPA and the state drinking water primacy agency (water sector), state public utility commissions, and the SEC for investor-owned utilities. Set the intake flags `nerc_registered_entity`, `doe_electric_utility`, `tsa_pipeline_owner`, or `water_utility` so the right clocks load.

## Typical scenarios

- Compromise of an internet-facing remote access gateway with a known exploited vulnerability, followed by credential theft and movement toward the corporate domain and the jump hosts that sit in front of the control network. The scenario tests whether the IT to OT boundary holds and who can order it cut.
- Ransomware in the corporate network that takes down the customer information system, outage management, and work order systems while the control center stays up. The pressure is on whether operations can run manually and whether the DOE-417 and CIP-008 determinations are made on time.
- Vendor or integrator remote session abused to reach an energy management system or a substation gateway. The scenario tests third-party access controls, Electronic Access Control or Monitoring System logging, and the attempt-to-compromise determination.
- Suspicious activity inside the control network (unexpected engineering workstation logons, new firmware on relays, or historian anomalies) with no outage yet. The team must decide whether it is a Reportable Cyber Security Incident, an attempt to compromise, or neither, and do so with a timestamp.
- Pipeline control system disruption that forces manual operation of compressor or pump stations, testing the TSA Cybersecurity Coordinator role and the CISA report.
- Water utility treatment plant HMI exposed to the internet with changed setpoints, testing operator verification of chemical dosing and the state primacy agency relationship.

## Stakeholders and roles

Operations and engineering:
- Cyber Security Incident Response Lead (the incident commander named in the CIP-008 plan)
- Control Center Manager and the shift supervisor on duty; System Operations director
- OT and SCADA Engineering Lead; relay and protection engineering; field operations supervisor
- Water plant superintendent and licensed operators (water utilities); pipeline control room supervisor (pipelines)

Security, compliance, and legal:
- Chief Information Security Officer and Chief Information Officer
- NERC CIP Compliance Officer and the internal compliance program lead
- Physical Security Manager
- TSA-designated Cybersecurity Coordinator and alternate (pipelines)
- General Counsel and outside counsel; Regulatory Affairs director (state commission relationship)

Executive and external:
- Chief Executive or General Manager; Chief Financial Officer; board risk committee chair
- Communications and Customer Affairs Lead
- Reliability Coordinator and Balancing Authority contacts; E-ISAC member representative
- Cyber insurance carrier; managed security provider if one is retained; mutual assistance coordinator

## Hardest decisions

- Cutting the IT to OT link: severing the connection stops lateral movement but blinds the control center to outage management, weather, and market data, and may force manual operations. Who has the authority, and is the control room staffed for it?
- The CIP-008 determination: the one-hour clock starts at determination, not detection. Teams delay the determination to gather certainty, which is exactly what the regulator will question afterward. The plan must say who determines and how it is timestamped.
- Which DOE-417 tier: a cyber event that could potentially impact reliability is a six-hour Normal Report; one that causes interruptions is a one-hour Emergency Alert. Under pressure, teams either over-report every alert or wait for an outage.
- Manual operations versus shutdown: staying energized on manual control carries safety and reliability risk; de-energizing or shutting a pipeline carries customer and economic harm. Operations and security see this differently.
- Evidence versus restoration: rebuilding the jump host or the engineering workstation destroys the only record of the attack vector, which CIP-008 Part 4.1 requires the entity to report.
- Public and customer messaging during an outage that may be cyber-caused: the communications team wants to say "weather" or "equipment"; counsel wants to say nothing; the state commission wants a call first.

## Notification clocks

`clocks.yaml` is the source of truth. GDPR, SEC Form 8-K, state breach laws, and CIRCIA come from `clocks_common.yaml` and load when `includes_common: true`. Summary of the pack's own clocks:

| id | Goes to | Deadline | Tier |
|---|---|---|---|
| nerc_cip_008_one_hour | E-ISAC and CISA | 1 hour after determination of a Reportable Cyber Security Incident | researched |
| nerc_cip_008_attempt_next_calendar_day | E-ISAC and CISA | end of the next calendar day after determination of an attempt to compromise (24 hour floor) | researched |
| nerc_cip_008_update_seven_days | E-ISAC and CISA | 7 calendar days after new or changed attributes are determined | researched |
| doe_oe417_emergency_alert_one_hour | DOE Emergency Operations Center | 1 hour (criteria 1 to 9, including a Reportable Cyber Security Incident) | researched |
| doe_oe417_normal_report_six_hours | DOE Emergency Operations Center | 6 hours (criteria 10 to 13, including a cyber event that could impact reliability) | researched |
| doe_oe417_attempted_cyber_compromise_next_day | DOE Emergency Operations Center | end of the next calendar day after determination (criterion 14, 24 hour floor) | researched |
| doe_oe417_final_report_72h | DOE Emergency Operations Center | 72 hours after the incident | researched |
| tsa_pipeline_sd_incident_report | CISA Central | 72 hours after identification under SD Pipeline-2021-01G (earlier versions said 24 hours; check the version in force) | researched |
| epa_water_sector_guidance | EPA and state primacy agency | no federal deadline confirmed; state rules vary | researched |

A DOE-417 filed with the sharing box on Schedule 2 line W selected satisfies CIP-008 reporting for criteria 2 and 14, so one well-timed filing can close two clocks.

## Exercise requirements

- NERC CIP-008-6 Requirement R2 Part 2.1: test each Cyber Security Incident response plan at least once every 15 calendar months, by responding to an actual Reportable Cyber Security Incident, with a paper drill or tabletop exercise, or with an operational exercise. Part 2.2 requires using the plan during the exercise and documenting deviations; the lessons-learned report is the evidence (`nerc_cip_008_r2_test_15_months`, `nerc_cip_008_r2_document_deviations`).
- NERC CIP-008-6 Requirement R3 (not drafted as a requirement here): plan updates and notification of people with a defined role within 90 calendar days of a test or actual incident, per the Violation Severity Levels table on pages 15 to 17 of the standard.
- GridEx: the E-ISAC hosts North America's largest grid security exercise every two years. Participation is voluntary practice, not a requirement, and a GridEx move-zero cycle is a natural time to run this pack (`nerc_gridex_biennial_practice`).
- Pipeline operators: TSA Security Directive Pipeline-2021-02 series requires cybersecurity contingency planning and testing; it was not fetched for this draft and should be added when the pack is human-checked.
- Water utilities: America's Water Infrastructure Act emergency response plans are referenced on the EPA page, with no exercise cadence confirmed here.

## Sector vocabulary

Compliance terms (use them exactly, the compliance officer will):
- BES Cyber System, High and Medium Impact, EACMS (Electronic Access Control or Monitoring System), ESP (Electronic Security Perimeter), PSP (Physical Security Perimeter)
- Reportable Cyber Security Incident, attempt to compromise, Responsible Entity, Regional Entity, Violation Severity Level
- Form DOE-417 Emergency Alert, Normal Report, Attempted Cyber Compromise, System Report, Final Report; Schedule 2 line W sharing election
- Cybersecurity Coordinator (TSA), Security Directive Pipeline-2021-01 series, CISA Central report

Operations terms (use them so the injects sound like the control room):
- Balancing Authority, Reliability Coordinator, Transmission Operator, Generator Operator, Distribution Provider
- EMS (energy management system), SCADA, historian, ICCP link, RTU, IED and protective relay, engineering workstation, jump host
- Control center and backup control center, manual operations, load shed, islanding, black start, mutual assistance, storm mode
- Compressor station, pump station, pipeline SCADA, leak detection, HMI, PLC, chemical dosing, treatment plant, primacy agency, AWIA risk and resilience assessment

## Sources

- https://www.nerc.com/pa/Stand/Reliability%20Standards/CIP-008-6.pdf (NERC CIP-008-6 standard PDF; R2 Part 2.1 on page 7, R4 Parts 4.1 to 4.3 on pages 11 to 12), read 2026-11-03
- https://doe417.pnnl.gov/files/DOE417_Form_Instructions.pdf (Form DOE-417 instructions, OMB 1901-0288 expiring 05/31/2027; the DOE page at oe.netl.doe.gov refused the connection), read 2026-11-03
- https://www.tsa.gov/sd-and-ea (TSA Security Directives and Emergency Amendments index listing SD Pipeline-2021-01G under January 15, 2026), read 2026-11-03
- https://www.tsa.gov/sites/default/files/signed_security-directive-pipeline-2021-01g-and-transmittal-memo_508c.pdf (SD Pipeline-2021-01G, effective January 16, 2026 through January 15, 2027), read 2026-11-03
- https://tsa.gov/sites/default/files/sd-pipeline-2021-01d.pdf (SD Pipeline-2021-01D, effective May 29, 2024, superseded; 24 hour reporting language), read 2026-11-03
- https://www.epa.gov/waterresilience/epa-cybersecurity-water-sector (EPA water sector cybersecurity page, guidance only), read 2026-11-03
- https://www.nerc.com/programs/e-isac/grid-ex (GridEx program page; the older nerc.com/pa/CI/ESISAC/Pages/GridEx.aspx URL redirects here), read 2026-11-03
- https://www.cisa.gov/topics/cyber-threats-and-advisories/information-sharing/cyber-incident-reporting-critical-infrastructure-act-2022-circia (CIRCIA status, used by clocks_common.yaml), read 2026-11-03
