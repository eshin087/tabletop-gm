# Valley Regional Health System Cybersecurity Incident Response Plan

Document control: Version 3.2, approved by the Information Security Steering Committee. Owner: Chief Information Security Officer. Review cycle: annual. This document is synthetic and exists only to demonstrate Tabletop GM's policy ingest. Valley Regional Health System is a fictional organization.

## 1. Purpose and scope

This plan defines how Valley Regional Health System (VRHS) detects, declares, escalates, contains, recovers from, and reports cybersecurity incidents affecting its information systems, medical devices, and the protected health information entrusted to it. It applies to all workforce members, contractors, and business associates with access to VRHS systems, at both hospital campuses and all fourteen clinics.

## 2. Roles and responsibilities

### 2.1 Incident Commander

The Chief Information Security Officer (CISO) serves as Incident Commander for all cybersecurity incidents. The Incident Commander has the authority to declare a cybersecurity incident, assign its severity level, activate the Cyber Incident Response Team, and direct containment actions. When the CISO is unavailable, the Director of Security Operations serves as Incident Commander.

### 2.2 Cyber Incident Response Team

The Cyber Incident Response Team (CIRT) consists of the Incident Commander, the Director of Security Operations, the Director of Infrastructure, the Privacy Officer, the Director of Clinical Engineering, and a representative from General Counsel. Additional members are added by the Incident Commander as the incident requires.

### 2.3 Decision authorities

The Chief Information Officer (CIO) authorizes the shutdown or isolation of any production clinical system, including the electronic health record, after consulting the Chief Medical Information Officer. In a SEV1 incident the Incident Commander may isolate a system immediately and must notify the CIO within 30 minutes of doing so.

The Privacy Officer owns the breach risk assessment and decides, with General Counsel, whether an incident is a reportable breach of protected health information.

General Counsel is the only role authorized to communicate with regulators, law enforcement, and the cyber insurance carrier on behalf of VRHS.

The Chief Executive Officer approves any public statement, patient-facing notification, or media response, on the recommendation of the Director of Communications and General Counsel.

## 3. Severity levels

VRHS classifies cybersecurity incidents into four severity levels.

SEV1 (Critical): confirmed compromise or loss of availability of a clinical system, a system containing protected health information, or the identity infrastructure (Active Directory), or any ransomware detonation. SEV1 incidents require activation of the Hospital Command Center.

SEV2 (High): confirmed compromise of a non-clinical business system, a compromised privileged account, or suspected unauthorized access to protected health information without confirmed loss of availability.

SEV3 (Moderate): a single compromised user account, a contained malware infection on one endpoint, or a policy violation with no evidence of data access.

SEV4 (Low): phishing reports, failed intrusion attempts, and vulnerability findings with no evidence of exploitation.

The Incident Commander assigns the severity level at declaration and may raise or lower it as facts develop. Every change in severity is recorded in the incident log with the time and the reason.

## 4. Escalation and notification timing

### 4.1 Internal escalation

Security Operations notifies the Incident Commander within 15 minutes of identifying a suspected SEV1 or SEV2 incident.

The Incident Commander notifies the CIO and the Privacy Officer within 30 minutes of declaring a SEV1 or SEV2 incident.

The CIO notifies the Chief Executive Officer and General Counsel within 1 hour of a SEV1 declaration. The Chief Executive Officer informs the Board Chair within 24 hours of a SEV1 declaration.

### 4.2 Hospital Command Center

For any SEV1 incident, the Incident Commander requests activation of the Hospital Command Center through the Emergency Management Director. Clinical downtime procedures are activated by the Chief Nursing Officer for affected units.

### 4.3 Cyber insurance

General Counsel notifies the cyber insurance carrier within 24 hours of a SEV1 or SEV2 declaration and before any outside forensic firm, breach counsel, or negotiator is engaged.

### 4.4 Law enforcement

General Counsel decides whether to notify the FBI field office. Notification is expected for any ransomware incident and any incident with evidence of data exfiltration.

## 5. Breach assessment and regulatory notification

### 5.1 Breach risk assessment

The Privacy Officer completes the four-factor breach risk assessment within 10 business days of the Incident Commander confirming that protected health information was accessed, acquired, used, or disclosed without authorization. The assessment is documented in the incident record.

### 5.2 Regulatory and individual notification

Where the assessment concludes that a reportable breach occurred, VRHS notifies affected individuals, the Secretary of Health and Human Services, and, where required, the media and state agencies. VRHS's internal standard is to issue individual notifications within 45 calendar days of discovery, which is stricter than the regulatory outer limit. General Counsel owns the regulatory notifications and the Privacy Officer owns the individual notification letters.

### 5.3 Business associates

Where the incident originates with a business associate, the Privacy Officer confirms that the business associate agreement's notification clause was met and records the date VRHS was notified as the discovery date.

## 6. Containment

### 6.1 Principles

Containment actions preserve evidence. Before any affected system is rebuilt or restored, Security Operations captures a forensic image or confirms that the outside forensic firm has done so.

### 6.2 Standard containment actions

Security Operations isolates the affected system from the network, disables compromised accounts, resets credentials for all privileged and service accounts that authenticated to the affected system in the preceding 30 days, and blocks the attacker infrastructure at the perimeter.

### 6.3 Clinical systems

Isolation of a clinical system follows the decision authority in section 2.3. The Director of Clinical Engineering isolates affected medical devices and confirms with nursing leadership that patient care has moved to downtime procedures.

## 7. Recovery

### 7.1 Recovery objectives

The electronic health record has a recovery time objective of 4 hours and a recovery point objective of 15 minutes. Active Directory has a recovery time objective of 2 hours. The picture archiving and communication system has a recovery time objective of 8 hours. Business systems, including email and the revenue cycle platform, have a recovery time objective of 24 hours.

### 7.2 Restore order

Systems are restored in this order: identity infrastructure (Active Directory), network services, the electronic health record and its interface engine, ancillary clinical systems, and then business systems. The CIO may change the order with the agreement of the Chief Medical Information Officer.

### 7.3 Backup validation

Before restoring from backup, the Director of Infrastructure confirms that the backup predates the earliest known compromise and that a test restore of the backup has completed successfully.

## 8. Ransomware playbook

Step 1. Security Operations isolates affected systems and preserves the ransom note and any attacker communication as evidence.

Step 2. The Incident Commander declares a SEV1 incident and requests Hospital Command Center activation.

Step 3. The Director of Infrastructure verifies that backups are offline and unaffected.

Step 4. General Counsel notifies the cyber insurance carrier and the FBI field office.

Step 5. Security Operations resets all privileged credentials and rebuilds the identity infrastructure from a known-good state.

Step 6. The CIO approves the restore order under section 7.2.

Step 7. The Privacy Officer begins the breach risk assessment under section 5.1.

## 9. Communications

### 9.1 Internal communications

The Director of Communications issues workforce updates at least every 4 hours during a SEV1 incident using the pre-approved workforce notice template, after review by the Incident Commander.

### 9.2 External communications

All external statements, including holding statements to the media, are drafted by the Director of Communications, reviewed by General Counsel, and approved by the Chief Executive Officer before release. The pre-approved holding statement template is maintained in the communications shared folder.

### 9.3 Patient communications

Patient-facing notices about delayed or diverted care are approved by the Chief Medical Officer and the Chief Executive Officer.

## 10. Documentation and after-action review

The Incident Commander maintains the incident log, including the time of every decision, who made it, and who was notified. An after-action review is held within 10 business days of incident closure and its findings are reported to the Information Security Steering Committee.

## 11. Plan maintenance and testing

This plan is reviewed annually and exercised at least once per year through a tabletop exercise that includes clinical, executive, and technical participants.
