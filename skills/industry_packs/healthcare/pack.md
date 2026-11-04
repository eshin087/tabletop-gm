# Healthcare and health systems pack

Tier: researched (per-clock tiers live in `clocks.yaml`; promote after a human check)
Last reviewed: 2026-11-03
Owner: Eric (gcd)

Story material lives here; every deadline lives in `clocks.yaml`; scoring defaults live in `defaults.yaml`.

## Who this pack is for

Hospitals, health systems, physician groups, ambulatory and behavioral health providers, and the business associates that hold protected health information for them. Fits organizations from a single community hospital to a multi-hospital system. The regulators and standards that matter: HHS Office for Civil Rights (HIPAA Privacy, Security, and Breach Notification Rules), CMS Conditions of Participation (emergency preparedness), state health departments (New York, California, and others with their own incident rules), state attorneys general (state breach laws), the Joint Commission, and the HHS 405(d) Health Industry Cybersecurity Practices. Health plans and insurers also load the insurance pack; business associates set the `business_associate` flag.

## Typical scenarios

- Ransomware across the electronic health record and its interfaces, forcing clinical downtime procedures and an EMS diversion decision. The most common and most consequential pattern in the sector.
- Compromise of an internet-facing access gateway (VPN, remote access, or patient portal edge device) with a known exploited vulnerability, followed by credential theft and movement toward the domain and the EHR database.
- Business associate incident: a billing, transcription, or revenue-cycle vendor reports that patient data it holds was accessed, and the covered entity owns the notification decision without owning the evidence.
- Business email compromise against the revenue cycle or a vendor payment, where the first signal is a redirected payment rather than an alert.
- Medical device or clinical network segment incident: imaging, infusion, or lab analyzers on a flat network segment, where isolation decisions affect patient care in real time.

## Stakeholders and roles

Hospital Incident Command System roles (Incident Commander, Operations, Planning, Logistics, Finance), the Chief Information Security Officer, Chief Information Officer, Privacy Officer, Chief Medical Information Officer, Chief Nursing Officer, Chief Medical Officer, General Counsel and outside breach counsel, Compliance Officer, Director of Communications, Chief Executive Officer, Chief Financial Officer, Director of Clinical Engineering (medical devices), Emergency Management Director, Risk Management, department directors for pharmacy, laboratory, and imaging, the cyber insurance carrier, and the managed security provider if one is retained.

## Hardest decisions

- EMS diversion and surgical cancellations: going on diversion protects patients when systems are degraded, but it is a public act that starts the media clock and shifts load to neighboring hospitals. Teams delay it because it feels like admitting failure.
- Cutting interfaces: shutting the lab, pharmacy, and imaging interfaces stops lateral movement but turns a cyber incident into a clinical safety incident. Who has the authority, and have the downtime forms been printed?
- The breach risk assessment: HIPAA presumes a breach unless a documented four-factor assessment shows a low probability of compromise. Teams argue about whether data was "really" exfiltrated instead of starting the assessment.
- Paying the ransom: the decision belongs to the chief executive with counsel, insurer, and law enforcement input, and it has sanctions exposure. Teams discover mid-incident that nobody knows who holds the pen.
- Restore order: EHR first, or the domain first, or the systems that keep the emergency department open? Backups that were never tested fail here.
- Patient communication: when to tell patients, what to say about delayed care, and who approves the statement.

## Notification clocks

`clocks.yaml` is the source of truth. Summary:

| id | Goes to | Deadline | Tier |
|---|---|---|---|
| hipaa_individual_notice | Affected individuals | 60 calendar days from discovery, without unreasonable delay | researched |
| hipaa_hhs_notice_500_or_more | HHS Secretary (500 or more) | Contemporaneous with individual notice, 60 days | researched |
| hipaa_media_notice | Prominent media (more than 500 residents of a state) | 60 calendar days | researched |
| hipaa_business_associate_notice | Business associate to covered entity | 60 calendar days (contracts are usually shorter) | researched |
| ny_hospital_cyber_incident_72h | New York State Department of Health | 72 hours from determination | researched |
| ca_health_facility_unauthorized_access_15bd | California Department of Public Health and patients | 15 business days from detection | researched |
| ftc_hbnr_individual_notice | Individuals (non-HIPAA health records vendors) | 60 calendar days | researched |

GDPR, SEC Form 8-K (public health systems), state breach notification laws, and CIRCIA come from `clocks_common.yaml` and apply by intake answers (countries, states, public company, flags).

## Exercise requirements

- CMS Emergency Preparedness Rule, 42 CFR 482.15(d)(2): hospitals run an annual full-scale exercise plus an additional annual exercise, which may be a facilitator-led tabletop exercise. A cyber scenario qualifies when it tests the emergency plan.
- HIPAA Security Rule, 45 CFR 164.308(a)(7)(ii)(D): periodic testing and revision of contingency plans; 164.308(a)(6)(i): security incident procedures.
- HHS 405(d) Health Industry Cybersecurity Practices and the Joint Commission emergency management chapter are expectations examiners and surveyors ask about; they are guidance, not clocks.

## Sector vocabulary

Downtime procedures, downtime forms, EHR (electronic health record), ADT (admit, discharge, transfer), HL7 interfaces, interface engine, PACS (imaging), LIS (laboratory), pharmacy system, CPOE (computerized provider order entry), MAR (medication administration record), EMS diversion, HICS (Hospital Incident Command System), command center, PHI (protected health information), minimum necessary, business associate, BAA (business associate agreement), covered entity, breach risk assessment (four-factor), OCR (Office for Civil Rights), breach portal, Health-ISAC, clinical engineering, biomed, infusion pump, patient safety event, Joint Commission survey.

## Sources

- https://www.law.cornell.edu/cfr/text/45/164.404 (read 2026-11-03; mirror of eCFR 45 CFR 164.404)
- https://www.law.cornell.edu/cfr/text/45/164.406 (read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/45/164.408 (read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/45/164.410 (read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/45/164.308 (read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/42/482.15 (read 2026-11-03)
- https://www.law.cornell.edu/cfr/text/16/318.4 (read 2026-11-03)
- https://healthweb-back.health.ny.gov/facilities/hospital/cybersecurity/ (read 2026-11-03)
- https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=1280.15 (fetch blocked 2026-11-03; verify by hand)
