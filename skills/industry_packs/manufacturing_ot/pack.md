# Manufacturing and operational technology pack

Tier: researched (per-clock tiers live in `clocks.yaml`)
Last reviewed: 2026-11-03
Owner: unassigned

Story material for manufacturers and other operators of industrial control systems lives here; every deadline lives in `clocks.yaml`; scoring defaults live in `defaults.yaml`. Drafted by the `pack_research` skill from the sources listed at the end and not yet human-checked.

## Who this pack is for

Discrete and process manufacturers, from a single plant with 200 employees and one system integrator to a multinational with dozens of sites, plus the OT-heavy operators that share their problems: plant railroads, in-plant pipelines, utilities on site, and contract manufacturers. Their estate mixes an enterprise network (ERP, email, engineering file shares) with plant networks (PLCs, HMIs, SCADA or DCS, historians, MES) that were built for uptime rather than patching and are reachable by vendors over remote access. The bodies that matter are CISA (CIRCIA, and TSA directive reporting for designated pipeline and rail owners), TSA for those owners, the SEC for public manufacturers, EU member-state CSIRTs under NIS2 for manufacturing sectors in Annex II, and the ISA/IEC 62443 standards that customers and insurers use as the benchmark for an OT security program. CIRCIA, SEC Form 8-K, state breach laws, and GDPR come from `clocks_common.yaml`. Defense contractors handling CUI also carry the DFARS 252.204-7012 72-hour clock, which lives in the `federal_contractors` pack and is referenced here, not duplicated.

## Typical scenarios

- Ransomware across the plant historian and MES, so the lines can run but nobody can see what they made or release product to shipping, forcing a choice between running blind and stopping.
- Compromise of a system integrator's remote access jump host that reaches PLC engineering workstations at several sites, discovered when one site notices an unscheduled controller download.
- Ransomware on the ERP and shipping systems while the lines keep running, so finished goods pile up and customers' just-in-time schedules break within a shift.
- Theft of engineering drawings, process recipes, and supplier pricing (trade secrets) through a departing employee's cloud sync, surfacing when a competitor's bid looks familiar.
- An unexplained change to safety instrumented system configuration found during a maintenance window, raising the question of whether it was an intrusion, a contractor error, or both, and whether the plant can restart.
- Business email compromise at a tier 2 supplier that sends altered bank details and fraudulent purchase orders through the EDI channel.

## Stakeholders and roles

CEO; CFO (business interruption claim, disclosure); CISO; Head of Security Operations or IT Director as incident commander; Plant Manager (production halt, safe shutdown, restart authorization); OT Engineering Lead or Controls Engineering Lead (control network isolation, controller integrity, vendor access, logic restore); Environmental Health and Safety Lead; VP Manufacturing Operations (multi-site priorities); VP Supply Chain (customer commitments, supplier notices); Quality Director (batch quarantine, product release); General Counsel; Communications Lead; shift supervisors and union representatives.

Outside the building: the control system vendor's support line, the system integrator, OT forensics specialists, the cyber and business interruption insurers, CISA and TSA for designated owners, key customers and OEMs, and process safety regulators if the incident becomes a safety event.

## Hardest decisions

1. Stop the line or run blind: isolating the historian and MES means lines run without recipe control and lot traceability; stopping means missed shipments, a cold restart, and scrap.
2. Cut vendor remote access: it closes the attacker's most likely path and also removes the integrator's ability to help diagnose and restore, often in the same hour.
3. Trust the controllers: without a verified logic baseline nobody can say whether PLC programs or setpoints were changed; a full reload across hundreds of controllers takes days and needs the vendor the team just locked out.
4. Report to CISA or TSA before the picture is clear: the TSA directives run from the moment the incident is identified, early reports are thin, and the report is shared across agencies; waiting for certainty risks missing the window.
5. Declare a safety event: if the incident could have touched a safety system, EHS and process safety regulators have their own obligations and the restart needs a safety review, which the cyber team may not think to trigger.

## Notification clocks

`clocks.yaml` is the source of truth; this is a summary. CIRCIA (when the CISA rule is in force), SEC Form 8-K Item 1.05 for public manufacturers, US state breach laws for employee or customer PII, GDPR for EU personal data, and PCI card brand conventions where a direct-to-consumer channel takes cards all come from `clocks_common.yaml`. The DFARS 252.204-7012 72-hour report to the DoD for cyber incidents affecting covered defense information lives in the `federal_contractors` pack; set that pack alongside this one for a defense supplier. CFATS is not included: CISA's program page states that the statutory authority expired in July 2023, that CISA cannot enforce the regulations, and that reauthorization is pending, so there is no clock to code.

| Clock id | Goes to | Deadline | Tier |
|---|---|---|---|
| `mfg_tsa_pipeline_cisa_incident_report` | CISA Central (TSA SD Pipeline-2021-01G) | 72 hours from identifying the incident; supplemental information within 24 hours | researched |
| `mfg_tsa_rail_cisa_incident_report` | CISA Central (TSA SD 1580-21-01E freight; 1582-21-01E passenger and transit) | 72 hours from identifying the incident; supplemental information within 24 hours | researched |
| `mfg_nis2_art23_early_warning` | member-state CSIRT or competent authority | 24 hours from awareness of a significant incident | researched |
| `mfg_nis2_art23_incident_notification` | member-state CSIRT or competent authority | 72 hours from awareness | researched |
| `mfg_nis2_art23_final_report` | member-state CSIRT or competent authority | one month after the incident notification | researched |

Flags used: `tsa_pipeline_owner` (TSA has notified the organization that its pipeline system or LNG facility is critical), `tsa_rail_owner` (a freight railroad carrier, passenger railroad, or rail transit system covered by 49 CFR 1580.101 or 1582.101 or otherwise designated), `nis2_essential_or_important_entity`.

Intake prompts that decide which clocks fire:

- Has TSA notified the organization that any pipeline, LNG facility, or railroad it operates is critical or covered (sets `tsa_pipeline_owner` or `tsa_rail_owner`)?
- Does the organization have EU plants or entities in an Annex II manufacturing sector above the size thresholds (sets `nis2_essential_or_important_entity`)?
- Is the organization public, and does it hold CUI under a defense contract (SEC 8-K from the common file; DFARS from the `federal_contractors` pack)?
- Which plants share a domain, a historian, or a vendor remote access path (decides how far a single compromise can travel)?

A note on the TSA figure: the research brief for this pack expected 24 hours. The current directives, read on 2026-11-03, say 72 hours; the 24-hour window applied through the 2025 series letters and was changed in Pipeline-2021-01F and the matching rail renewals, with 24 hours now applying only to supplemental information. The series renews roughly annually, so the verifier should re-open the directives page before each exercise.

## Exercise requirements

- ISA/IEC 62443-2-1 (2024), security program requirements for IACS asset owners: no notification clock, but the OT security program it describes includes incident response, and a tabletop with plant and controls staff is the usual evidence (`mfg_isa_iec_62443_security_program`; the overview page lists the parts, the requirement text is paid and must be verified).
- TSA SD Pipeline-2021-02G, Section F.1.e: exercise the Cybersecurity Incident Response Plan no less than annually, testing at least two plan objectives with the named positions as active participants (`mfg_tsa_pipeline_annual_exercise`).
- TSA SD 1580-21-01E and 1582-21-01E, Section II.D.3: the same annual situational exercise requirement for rail owners (`mfg_tsa_rail_annual_exercise`).
- Cyber insurers and OEM customer security addenda commonly require an annual test of the plan and evidence of OT network segmentation; conventions, not coded.

## Sector vocabulary

PLC, HMI, SCADA, DCS, historian, MES, ERP, OT, IT/OT boundary, industrial DMZ, Purdue level, engineering workstation, controller logic, ladder logic, setpoint, safety instrumented system (SIS), safety PLC, lockout tagout, islanded operation, manual mode, line, cell, shift, changeover, batch record, lot traceability, recipe, golden image, jump host, vendor remote access, system integrator, OEM, tier 1 and tier 2 supplier.

Plant manager, maintenance window, scheduled outage, unplanned downtime, OEE, takt time, scrap, cold restart, EDI, advance ship notice, dock schedule, kanban, just-in-time, stock-out, allocation, force majeure, Cybersecurity Coordinator, Critical Cyber System, cybersecurity incident, significant incident, essential and important entities.

## Sources

- https://www.tsa.gov/sd-and-ea (read 2026-11-03; current series letters and dates for the pipeline and rail cybersecurity directives)
- https://www.tsa.gov/sites/default/files/signed_security-directive-pipeline-2021-01g-and-transmittal-memo_508c.pdf (read 2026-11-03; Section II.C, 72 hours, effective January 16, 2026)
- https://www.tsa.gov/sites/default/files/signed_security-directive-1580-21-01e-and-transmittal-memo_508c.pdf (read 2026-11-03; Section II.C.2 and II.D.3)
- https://www.tsa.gov/sites/default/files/signed_security-directive-1582-21-01e-and-transmittal-memo_508c.pdf (read 2026-11-03; Section II.C.2 and II.D.3)
- https://www.tsa.gov/sites/default/files/signed_security_directive_pipeline-2021-02g_and_transmittal_memo_508c.pdf (read 2026-11-03; Section F.1.e, effective May 3, 2026)
- https://www.tsa.gov/sites/default/files/signed_security-directive-pipeline-2021-01f-and-transmittal-memo-508c-1.pdf (read 2026-11-03; superseded, documents the change from 24 to 72 hours)
- https://www.tsa.gov/sites/default/files/signed_security-directive-1582-21-01d-and-transmittal-memo-508c-1.pdf (read 2026-11-03; superseded, same change for rail)
- https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022L2555 (read 2026-11-03; NIS2 Article 23 and Annex II point 5)
- https://www.isa.org/standards-and-publications/isa-standards/isa-iec-62443-series-of-standards (read 2026-11-03; series overview and part titles)
- https://www.cisa.gov/resources-tools/programs/chemical-facility-anti-terrorism-standards-cfats (read 2026-11-03; CFATS authority expired, not reauthorized)
- Attempted and not read (HTTP 403 on 2026-11-03): https://www.iec.ch/blog/understanding-iec-62443
