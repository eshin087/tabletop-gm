# Retail and e-commerce pack

Tier: researched (per-clock tiers live in `clocks.yaml`)
Last reviewed: 2026-11-03
Owner: unassigned

Story material for retailers and e-commerce operators lives here; every deadline lives in `clocks.yaml`; scoring defaults live in `defaults.yaml`. Drafted by the `pack_research` skill from the sources listed at the end and not yet human-checked.

## Who this pack is for

Brick-and-mortar chains, omnichannel retailers, pure-play e-commerce operators, and franchise systems, from a regional chain of 20 stores to a national retailer with thousands of locations and a marketplace. They run point-of-sale lanes, e-commerce checkout, loyalty and CRM platforms, order and warehouse management, and a long tail of store-level vendors with remote access. The bodies that matter are the PCI Security Standards Council (PCI DSS v4.0.1), the card brands acting through the acquiring bank, the FTC (the Safeguards Rule for retailers that extend store credit or otherwise act as non-bank financial institutions, and Section 5 generally), state attorneys general under state breach laws, and the SEC for public retailers. State breach laws, SEC Form 8-K, GDPR for EU customers, and CIRCIA are shared across packs and come from `clocks_common.yaml`.

## Typical scenarios

- Payment skimming code injected into the e-commerce checkout through a compromised third-party script, discovered by the acquirer's common-point-of-purchase analysis rather than by the retailer.
- Ransomware across store back-office servers and the order management system in peak season, forcing a choice between manual lanes and closing stores.
- Credential stuffing against customer accounts and the loyalty program, draining stored points and exposing saved addresses and partial card numbers.
- Compromise of a POS vendor's remote support tool that reaches every store's payment terminals at once.
- Gift card balance fraud through a flaw in the balance-check API, surfacing as a finance anomaly before security sees it.
- Warehouse management outage from a compromised integration account, stopping fulfillment while the website keeps taking orders.

## Stakeholders and roles

CEO; CFO (chargeback reserves, insurance, revenue at risk); CISO; Director of Security Operations as incident commander; VP Store Operations (lanes, fallback procedures, store closures, field communications); Head of Payments (acquirer and processor relationships, card brand notices, terminal fleet); VP Digital and E-commerce (checkout, site, third-party scripts); Head of Loyalty and CRM; General Counsel; Privacy Officer; Communications and PR; Loss Prevention; supply chain and fulfillment lead; franchisee council where relevant.

Outside the building: the acquiring bank, the payment processor and POS vendor, a PCI Forensic Investigator if the brands require one, state attorneys general, and the cyber insurer.

## Hardest decisions

1. Close lanes or keep selling: stopping card acceptance limits cardholder exposure, but every hour of closed lanes in peak season is measurable lost revenue, and manual fallback procedures are rarely practiced.
2. When to call the acquirer: the Visa clock runs from reasonable suspicion, not confirmation, and the call starts a process the retailer no longer controls (forensic investigator, assessments, possible fines); waiting risks a larger assessment and a reputation for hiding it.
3. Pull the third-party checkout scripts: removing the tag manager or analytics scripts stops the skimmer and also breaks conversion tracking, fraud screening, and marketing attribution.
4. Speak to customers before the forensics finish: consumers learn of the breach from their banks' reissued cards; a retailer that stays silent looks evasive, one that speaks early may contradict the forensic findings.
5. Who owns the PCI scope question: whether the compromised system was inside the cardholder data environment decides whether this is a card brand matter at all, and the honest answer is often that the network diagram is stale.

## Notification clocks

`clocks.yaml` is the source of truth; this is a summary. US state breach laws, SEC Form 8-K Item 1.05 for public retailers, GDPR for EU customers, and CIRCIA come from `clocks_common.yaml`. If the common file also carries card brand conventions, keep one copy and remove the other so the timeline does not show the same clock twice.

| Clock id | Goes to | Deadline | Tier |
|---|---|---|---|
| `retail_visa_compromise_event_notice` | Visa Global Risk Investigations, through the acquirer | 3 calendar days from reasonable suspicion or confirmation of a Compromise Event | researched |
| `retail_visa_incident_report` | Visa and the acquiring bank | 3 calendar days after notifying Visa (Incident Report) | researched |
| `retail_ftc_safeguards_notice` | Federal Trade Commission | as soon as possible and no later than 30 days after discovery, 500 or more consumers, non-bank financial institutions only | researched |

Flags used: `nonbank_financial_institution` (the retailer issues store credit, finances purchases, or otherwise meets the Safeguards Rule definition of a financial institution).

Intake prompts that decide which clocks fire:

- Who is the acquiring bank and who at the retailer holds that relationship (the Visa clocks run through them)?
- Does the retailer store, process, or transmit PAN itself, or is checkout fully tokenized or outsourced (sets the PCI data type and scope)?
- Does the retailer extend store credit, finance purchases, or hold customer financial information (sets `nonbank_financial_institution`)?
- Which states and countries do affected customers live in (drives the common-file state and GDPR clocks)?
- Is the retailer public (SEC Form 8-K from the common file)?

Mastercard Account Data Compromise (ADC) program: the Security Rules and Procedures, Merchant Edition (chapter 10) and the ADC Event Management Best Practices document describe notifying Mastercard immediately on becoming aware of an ADC Event or Potential ADC Event, with 24 hours cited in the best-practices guide, through the ADC Reporting Form on Mastercard Connect. Neither document could be opened during research (the host returned HTTP 403 to every fetch), so this is guidance only and is not coded as a clock. notes: "source not fetched; verify before use". In the exercise, treat the acquirer call as the step that satisfies both brands and let the acquirer confirm the Mastercard timing.

American Express, Discover, and regional network rules were not researched for this draft. The Visa document also sets five-business-day windows for retaining a forensic investigator and delivering the preliminary report once Visa requires one; those are recorded in the clock notes rather than as separate clocks.

## Exercise requirements

- PCI DSS v4.0.1 Requirement 12.10.2: at least once every 12 months the security incident response plan is reviewed, updated as needed, and tested, including all elements in 12.10.1 (`retail_pci_dss_12_10_2_annual_test` in `clocks.yaml`; the document library page is the citation and the wording was confirmed in the v4.0 SAQ D). A tabletop that walks the plan end to end, including the payment brand procedures and the legal reporting analysis that 12.10.1 requires, is the usual evidence.
- Acquirer agreements and cyber insurance applications commonly ask whether the plan was tested in the last year; these are conventions, not coded.
- A Mastercard search snippet referenced an annual incident response plan test in the merchant security rules; not confirmed, not coded.

## Sector vocabulary

Cardholder data environment (CDE), PAN, track data, tokenization, point-to-point encryption (P2PE), EMV, card-not-present, POS lane, pin pad, terminal fleet, store controller, back office server, common point of purchase (CPP), acquirer, issuer, processor, gateway, chargeback, reissue, Window of Exposure, PCI Forensic Investigator (PFI), SAQ D, ROC, attestation of compliance.

Tag manager, checkout script, skimmer, bot management, credential stuffing, loyalty points, gift card balance, order management system (OMS), warehouse management system (WMS), buy online pick up in store, peak season, holiday code freeze, planogram, shrink, loss prevention, franchisee, store number, district manager, field operations.

## Sources

- https://www.pcisecuritystandards.org/document_library/ (read 2026-11-03; lists PCI DSS v4.0.1 and the v4.0 to v4.0.1 summary of changes)
- https://listings.pcisecuritystandards.org/documents/PCI-DSS-v4-0-SAQ-D-Merchant.pdf (read 2026-11-03; Requirement 12.10.1 and 12.10.2 wording)
- https://blog.pcisecuritystandards.org/updated-guidance-responding-to-a-data-breach (read 2026-11-03; Requirement 12.10 and the Responding to a Cardholder Data Breach guide)
- https://usa.visa.com/dam/VCOM/download/merchants/cisp-what-to-do-if-compromised.pdf (read 2026-11-03; Version 10.0, effective 25 June 2026, Sections A-1, A-2, A-4, B-4, B-5)
- https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-314/section-314.4 (read 2026-11-03 through the eCFR renderer API; the page itself redirects automated fetches)
- https://www.law.cornell.edu/cfr/text/16/314.4 (read 2026-11-03; mirror used to confirm 314.4(j))
- Attempted and not read (HTTP 403 on 2026-11-03): https://www.mastercard.com/content/dam/mccom/shared/business/support/rules-pdfs/SPME-Manual.pdf
- Attempted and not read (HTTP 403 on 2026-11-03): https://www.mastercard.com/content/dam/public/mastercardcom/globalrisk/pdf/ADC-Best-Practice-Manual.pdf
