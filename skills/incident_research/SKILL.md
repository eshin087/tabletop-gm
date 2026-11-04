---
name: incident_research
description: Optional prep step. Find two recent public incidents in the organization's sector, from cited public sources, to use as realism anchors for the scenario narrative. Patterns only; no victim names in any deliverable.
---

# Incident research

A scenario lands harder when the room recognizes how incidents in their sector actually unfold. This optional step gives the scenario designer two realism anchors. It is prep only: nothing from it is a fact about the organization being exercised.

## Method

1. Search for incidents in the organization's sector from the last 24 months. Prefer primary or authoritative sources: regulator enforcement actions, SEC 8-K Item 1.05 filings, HHS OCR breach portal entries, CISA advisories, court filings, and the affected organization's own statements. Use reputable reporting only to find them.
2. Pick two whose pattern matches the seed (same entry type, same kind of crown jewel, or the same business pressure).
3. For each, write in `out/incident_research.md` (gitignored): the source URL, the date, and the pattern in three lines: how it started, what made it worse, what decision the organization faced.

## How the anchors may be used

- As texture and pacing in `what_happens` and host lines: "the gateway alert looks like noise", "the vendor insists it is patched".
- As probing questions: "Organizations in your sector have faced this exact choice; what would you do?"
- Never as facts about the organization, never with the other organization's name, and never as a source citation in an inject (injects cite the seed or a labeled assumption).

## Never

- Never name a victim organization in the deck, guide, handout, or AAR.
- Never copy text from an article into a deliverable.
- Never present an inference about an incident as a confirmed fact.
