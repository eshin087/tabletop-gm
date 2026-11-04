# State, local, tribal, and K-12 public sector industry pack

Tier: researched (per-clock tiers live in `clocks.yaml`)
Last reviewed: 2026-11-03
Owner: unassigned

This pack covers state agencies, counties, cities, special districts, tribal governments, and K-12 school districts. Story material lives here; every deadline lives in `clocks.yaml`; scoring defaults live in `defaults.yaml`. State breach notification laws are shared across packs and live in `clocks_common.yaml`, so this file records only the sector-specific reporting rules that sit on top of them.

## Who this pack is for

Public bodies from a 40-person county IT shop or a single-district technology director up to a cabinet-level state agency with a dedicated security office. The regulators and standards bodies that matter are the state CIO or CISO and the statutory incident recipient in each state (for example the Texas Department of Information Resources, the Virginia Fusion Intelligence Center and VITA, the North Carolina Department of Information Technology, and the Florida Cybersecurity Operations Center), the state attorney general under the state breach law, the state education agency and its privacy officer for K-12 districts, CISA and MS-ISAC as federal and shared-service partners, and the FBI for criminal reporting. Tribal governments answer to their own councils and federal funding agencies rather than to state statutes, and the state clocks in this pack generally do not reach them.

## Typical scenarios

- Ransomware across county business systems: utility billing, permits, courts, and payroll stop at once, and the 12-hour and 48-hour state reports come due before anyone knows the scope.
- Business email compromise against vendor payments: a spoofed change-of-bank request diverts a capital project payment, discovered at reconciliation weeks later.
- Student information system compromise at a K-12 district: a vendor or stolen staff credential exposes student records, and the district must report to the state privacy officer within days while parents ask questions.
- Shared state network incident: a compromised partner agency on a shared network forces every connected body to decide whether to disconnect.
- Public safety dispatch outage from a cyber event: 911 call handling and records fall back to paper, and emergency management is activated alongside the security response.

## Stakeholders and roles

At the table (titles as the sector uses them):

- Agency Director, County Administrator, City Manager, Superintendent, or Tribal Administrator: owns the ransom decision, service shutdown, and the public declaration.
- State Chief Information Security Officer (or the state CIO's designee): directs statewide containment and can activate state resources.
- Agency Information Security Officer: declares the incident and rates severity.
- IT Director or Technology Director: owns system shutdown and the restore order.
- Agency General Counsel, County Attorney, or Tribal Attorney: owns notification obligations, law enforcement contact, and the public records response.
- Public Information Officer: owns public statements and media response.
- Emergency Management Director: decides EOC activation and any emergency declaration request.
- Records Management Officer or Clerk: owns records holds and public records handling.
- Clerk to the Board, Council, or Tribal Council: schedules the governing body briefing and any closed session.
- Data Protection Officer (K-12): makes the student data breach determination and owns parent notification.
- Finance Director or Treasurer: suspends payment systems and approves emergency procurement.

Outside the building: the state SOC, the state statutory incident recipient, MS-ISAC, the FBI field office, CISA, the state education agency's privacy officer, the cyber insurer or public entity risk pool, and shared service partners on the same network.

## Hardest decisions

- Whether to pay. Several states restrict or bar public bodies from paying a ransom (North Carolina G.S. 143-800 bars state agencies and local government entities from paying and requires consultation with DIT), and the political cost of either answer lands on elected officials.
- When to disconnect from a shared network. Cutting the link protects the state but stops services for residents, and the decision is often made by someone who does not own either side.
- What to say in public and when. Open meetings and public records laws mean the incident will be discussed in a public forum; the team must decide what can be withheld as security-sensitive and for how long.
- Whether to activate emergency management. Treating a cyber event as a disaster opens mutual aid and emergency procurement, but also raises expectations of a declaration.
- Who tells parents. In a K-12 district the privacy officer, the superintendent, and the vendor may each believe someone else owns the notice.

## Notification clocks

Summary only; `clocks.yaml` is the source of truth. GDPR, SEC Form 8-K, state breach laws, and CIRCIA come from `clocks_common.yaml` and are not repeated here. CIRCIA is listed by reference only: CISA's proposed rule was published April 4, 2024 and no final rule had taken effect at the time of drafting, so CISA reporting remains voluntary.

| Clock id | Goes to | Deadline | Tier |
| --- | --- | --- | --- |
| `tx_gov_2054_603_dir_notice` | Texas DIR (or Secretary of State for election data) | 48 hours after discovery; state agencies and local governments | researched |
| `tx_gov_2054_603_dir_cause_analysis` | Texas DIR | 10th business day after eradication, closure, and recovery | researched |
| `va_2_2_5514_fusion_center_report` | Virginia Fusion Intelligence Center | 24 hours after discovery; all public bodies | researched |
| `nc_143b_1379_dit_report` | North Carolina DIT | 24 hours after confirmation (flag `state_agency`) | researched |
| `fl_282_3185_ransomware_report` | Florida CSOC, FDLE Cybercrime Office, and the sheriff | 12 hours after discovery (flag `local_government`) | researched |
| `fl_282_3185_severity_incident_report` | Florida CSOC, FDLE Cybercrime Office, and the sheriff | 48 hours after discovery for severity 3 to 5 (flag `local_government`) | researched |
| `fl_282_3185_after_action_report` | Florida Digital Service | 1 week after remediation (flag `local_government`) | researched |
| `ny_8nycrr_121_10_cpo_report` | NYSED Chief Privacy Officer | 10 calendar days after discovery (flag `k12_district`) | researched |

FBI/IC3 and MS-ISAC reporting have no statutory deadline and are recorded as expected actions in `defaults.yaml`. North Carolina local government entities must report to DIT but the statute states no deadline, so no clock is recorded for them.

## Exercise requirements

No state statute requiring a tabletop exercise was confirmed for this pack. NIST SP 800-84, Guide to Test, Training, and Exercise Programs for IT Plans and Capabilities, is recorded as guidance under `nist_sp_800_84_exercise_guidance`. Florida 282.3185(3) requires annual cybersecurity training for local government employees, which is training rather than an exercise. Public entity risk pools and cyber insurers commonly ask for an annual tabletop at renewal; treat that as a contractual expectation and confirm it against the policy wording.

## Sector vocabulary

Statutory terms:

- Public body, political subdivision, local government entity, state agency, principal department: the entity classes each state statute reaches.
- Security incident, significant cybersecurity incident, ransomware incident, severity level: the reportable event classes.
- Discovery versus confirmation: the statutes start clocks from different moments; the timeline must record both.
- Statutory recipient: DIR, the Fusion Center and VITA, DIT, the Cybersecurity Operations Center, the Chief Privacy Officer.
- After-action report and cause analysis: the follow-up filings that come due after recovery.

Operational terms:

- State CISO, state SOC, statewide incident response hotline, MS-ISAC, IC3, CISA voluntary report.
- Emergency operations center (EOC), emergency declaration, mutual aid, emergency procurement.
- Open meeting, closed session, public records request, records hold.
- Utility billing, permits, payroll, public safety dispatch, student information system.
- Student data, teacher or principal APPR data, educational agency, data protection officer, third-party contractor, Data Incident Reporting Form.
- Public entity risk pool, shared service partner, shared state network.

## Sources

- https://capitol.texas.gov/tlodocs/88R/billtext/html/SB00271F.htm (enrolled SB 271, 88th Legislature, text of Texas Government Code 2054.603; read 2026-11-03)
- https://dir.texas.gov/information-security/cybersecurity-incident-management-and-reporting/sb-271-security-incident (Texas DIR page on SB 271 reporting, 48-hour and 10-day language; read 2026-11-03)
- https://law.lis.virginia.gov/vacode/title2.2/chapter55.3/section2.2-5514/ (Va. Code 2.2-5514, 24-hour report to the Fusion Center; read 2026-11-03)
- https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_143B/GS_143B-1379.html (N.C. Gen. Stat. 143B-1379, 24-hour state agency report; read 2026-11-03)
- https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_143/GS_143-800.html (N.C. Gen. Stat. 143-800, ransom payment prohibition and local government entity definition; read 2026-11-03)
- http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0200-0299/0282/Sections/0282.3185.html (Fla. Stat. 282.3185, 12-hour, 48-hour, and 1-week reports; read 2026-11-03)
- https://www.nysed.gov/sites/default/files/programs/data-privacy-security/annual-report-on-data-privacy-and-security-2022_0.pdf (NYSED Chief Privacy Officer 2022 annual report quoting 8 NYCRR 121.10(d); read 2026-11-03)
- https://www.nysed.gov/data-privacy-security/educational-agencies-report-data-incident (NYSED Report a Data Incident page and form; read 2026-11-03)
- https://www.nysed.gov/data-privacy-security/frequently-asked-questions-dpos (NYSED DPO FAQ referencing 121.10 notification deadlines; read 2026-11-03)
- https://www.nysenate.gov/legislation/laws/EDN/2-D (NY Education Law 2-d, subdivision 6, no day counts in the statute; read 2026-11-03)
- https://www.cisa.gov/topics/cyber-threats-and-advisories/information-sharing/cyber-incident-reporting-critical-infrastructure-act-2022-circia (CIRCIA rulemaking status; read 2026-11-03)
- https://csrc.nist.gov/pubs/sp/800/84/final (NIST SP 800-84; read 2026-11-03)
