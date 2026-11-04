# Colleges and universities industry pack

Tier: researched (per-clock tiers live in `clocks.yaml`)
Last reviewed: 2026-11-03
Owner: unassigned

This pack covers degree-granting colleges and universities, including community colleges and research universities. Story material lives here; every deadline lives in `clocks.yaml`; scoring defaults live in `defaults.yaml`. FERPA has no breach notification deadline, and this pack does not invent one: FERPA requires a record of each disclosure and nothing more. The deadlines that do apply to a campus come from the FTC Safeguards Rule and Federal Student Aid (for Title IV institutions), HIPAA for campus health (loaded from the healthcare pack), GDPR for EU students, and state breach laws (both from `clocks_common.yaml`).

## Who this pack is for

Institutions from a 2,000-student community college with a three-person IT security function to a research university with a hospital, a federated identity system, and sponsored research under federal contracts. The regulators that matter are the U.S. Department of Education and its Federal Student Aid office (Title IV participation, Program Participation Agreement, SAIG Enrollment Agreement), the Federal Trade Commission (Safeguards Rule, 16 CFR Part 314, which reaches Title IV institutions as financial institutions), the Department's Student Privacy Policy Office (FERPA), HHS Office for Civil Rights where campus health is a covered entity, state attorneys general under state breach laws, EU and UK supervisory authorities for EU and UK students, and federal research sponsors for controlled unclassified information. Public institutions are also public bodies under some state incident reporting statutes (for example Virginia 2.2-5514) and should load the public_sector pack alongside this one.

## Typical scenarios

- Ransomware across the student information system: registration, grading, and financial aid disbursement stop mid-term, and the question of paying arrives with a disbursement deadline attached.
- Business email compromise against financial aid refunds or vendor payments: a spoofed direct-deposit change diverts refunds or a construction payment.
- Stolen staff credentials used to pull applicant and financial aid records: the Safeguards Rule 500-consumer threshold and the FSA report are both in play within a day.
- Research network compromise touching sponsored data: a lab system holding controlled unclassified information is accessed, and sponsor reporting and export control questions arrive together.
- Campus health system breach: a third-party clinic platform exposes PHI, which brings the healthcare pack's HIPAA clocks into a campus incident.

## Stakeholders and roles

At the table (titles as the sector uses them):

- President or Chancellor: owns the ransom decision, campus closure, and the board briefing.
- Provost: owns academic continuity and any decision to cancel classes.
- Chief Information Officer or Vice President for Information Technology: owns system shutdown, network isolation, and the restore order.
- Chief Information Security Officer: rates severity and owns regulator notification.
- General Counsel: owns notification obligations, privilege, and law enforcement contact.
- Registrar: keeps the education record disclosure log and decides transcript holds.
- Dean of Students: owns student communication and support services.
- Director of Financial Aid: files the FSA breach report and decides disbursement holds.
- Vice President for Research: owns sponsor notification and research system isolation.
- Campus Health Privacy Officer: makes the PHI breach determination for campus health.
- Chief of Campus Police or Public Safety: owns criminal referral and physical security.
- Vice President for Communications: owns public statements and community messaging.
- Chief Financial Officer or Bursar: suspends payment systems and controls any ransom funding.

Outside the building: outside breach counsel, the cyber carrier and its forensics panel, the FBI field office, REN-ISAC, federal research sponsors and contracting officers, and the student information system, learning management, and financial aid vendors.

## Hardest decisions

- Whether to report to FSA before the scope is known. The Handbook says immediately and includes suspected breaches, so waiting for forensics is not an option, yet the first report shapes every later conversation with the Department.
- Treating FERPA as a notice law. Teams either assume FERPA requires a 60-day notice (it does not) or assume no notice is required at all (state breach laws and the Safeguards Rule usually require one). The registrar must log the disclosure either way.
- Shutting down the learning management system or federated login during term. Containment that stops classes creates academic continuity and accessibility problems the provost owns.
- Paying a ransom with a disbursement deadline looming. Financial aid funds and payroll create pressure that the president and CFO will feel before the forensics are finished.
- Telling research sponsors. Sponsor agreements and controlled unclassified information requirements can carry their own reporting expectations that the research office, not IT, knows about.

## Notification clocks

Summary only; `clocks.yaml` is the source of truth. GDPR, SEC Form 8-K, state breach laws, and CIRCIA come from `clocks_common.yaml` and are not repeated here.

| Clock id | Goes to | Deadline | Tier |
| --- | --- | --- | --- |
| `ftc_safeguards_314_4_j_ftc_notice` | Federal Trade Commission | 30 days after discovery of a notification event involving 500 or more consumers (flag `title_iv_institution`, min_affected 500) | researched |
| `fsa_breach_report_to_department` | Department of Education, Federal Student Aid | immediately, no hour count (flag `title_iv_institution`) | researched |
| `ferpa_99_32_disclosure_record` | Internal education record disclosure log | no deadline; recordkeeping only | researched |

FERPA has no notification deadline. HIPAA clocks for campus health (individual notice and notice to the Secretary under 45 CFR 164.404 and 164.408) are loaded from the healthcare pack when the institution flags campus health as a covered entity. GDPR Article 33 and 34 clocks for EU students come from the common file.

## Exercise requirements

- 16 CFR 314.4(h): establish a written incident response plan designed to promptly respond to, and recover from, any security event materially affecting customer information; the plan must be evaluated and revised following a security event. Recorded as `ftc_safeguards_314_4_h_incident_response_plan`. Institutions maintaining information on fewer than 5,000 consumers are exempt from this element.
- 16 CFR 314.4(d)(2): continuous monitoring or periodic penetration testing and vulnerability assessments; absent continuous monitoring, annual penetration testing and vulnerability assessments at least every six months. Recorded as `ftc_safeguards_314_4_d_2_testing`. This is a technical testing requirement; the tabletop supports the plan evaluation in 314.4(h).
- Federal Student Aid treats GLBA Safeguards findings in the annual compliance audit as administrative capability matters (GENERAL-23-09), so an untested plan can surface as an audit finding.

## Sector vocabulary

Regulatory terms:

- Title IV, Program Participation Agreement (PPA), SAIG Enrollment Agreement: the agreements that make the FSA report and the Safeguards Rule apply.
- Cybersecurity Breach Intake form: the FSA reporting channel.
- Customer information, notification event, qualified individual: Safeguards Rule terms; customer information is student financial aid data, not every education record.
- Education records, personally identifiable information from education records, directory information, eligible student, disclosure log: FERPA terms.
- Campus health covered entity, protected health information: the HIPAA overlap.
- Controlled unclassified information (CUI), export control, sponsored research: the research overlap.
- GLBA compliance audit finding: how an untested plan surfaces with the Department.

Operational terms:

- Student information system (SIS), learning management system (LMS), federated identity, single sign-on.
- Registrar hold, transcript hold, grading, registration, add and drop.
- Disbursement, refund, bursar, financial aid award, verification.
- Provost, academic continuity, class cancellation, term calendar.
- REN-ISAC, research network, lab system, principal investigator.

## Sources

- https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-314/section-314.4 (16 CFR 314.4(d)(2), (h), (j); eCFR blocks automated fetches, text confirmed via https://www.law.cornell.edu/cfr/text/16/314.4; read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/16/314.2 (16 CFR 314.2, definition of notification event; read 2026-11-03)
- https://www.ecfr.gov/current/title-34/subtitle-A/part-99/subpart-D/section-99.32 (34 CFR 99.32, record of disclosures; text confirmed via https://www.law.cornell.edu/cfr/text/34/99.32; read 2026-11-03)
- https://studentprivacy.ed.gov/sites/default/files/resource_document/file/checklist_data_breach_response_092012_0.pdf (PTAC Data Breach Response Checklist, FERPA does not require breach notification; read 2026-11-03)
- https://fsapartners.ed.gov/knowledge-center/fsa-handbook/2025-2026/vol2/ch7-record-keeping-privacy-electronic-processes (2025-2026 FSA Handbook, Volume 2, Chapter 7, immediate notification and intake form; read 2026-11-03)
- https://fsapartners.ed.gov/knowledge-center/fsa-handbook/2024-2025/vol2/ch7-record-keeping-privacy-electronic-processes (2024-2025 FSA Handbook, same language; read 2026-11-03)
- https://fsapartners.ed.gov/title-iv-program-eligibility/cybersecurity (FSA cybersecurity page linking the breach intake form; read 2026-11-03)
- https://fsapartners.ed.gov/title-iv-program-eligibility/cybersecurity/cybersecurity-breach-intake (Cybersecurity Breach Intake form fields; read 2026-11-03)
- https://fsapartners.ed.gov/knowledge-center/library/dear-colleague-letters/2015-07-29/protecting-student-information (GEN-15-18, SAIG Agreement immediate notification; read 2026-11-03)
- https://fsapartners.ed.gov/knowledge-center/library/dear-colleague-letters/2016-07-01/gen-16-12-subject-protecting-student-information (GEN-16-12; read 2026-11-03)
- https://fsapartners.ed.gov/knowledge-center/library/electronic-announcements/2023-02-09/updates-gramm-leach-bliley-act-cybersecurity-requirements (GENERAL-23-09, incident response plan element and audit findings; read 2026-11-03)
- https://fsapartners.ed.gov/knowledge-center/topics/fsa-cybersecurity-announcements-and-guidance (index of FSA cybersecurity announcements; read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/45/164.408 (HIPAA notice to the Secretary, by reference only; read 2026-11-03)
- https://www.cisa.gov/topics/cyber-threats-and-advisories/information-sharing/cyber-incident-reporting-critical-infrastructure-act-2022-circia (CIRCIA status, by reference only; read 2026-11-03)
