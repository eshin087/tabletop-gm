---
name: inject_style
description: How a good tabletop inject reads, with voice, pacing, realism rules, and before-and-after examples. Use when writing or polishing inject text and host lines.
---

# Inject style

An inject is a short piece of news that arrives at the table and forces a decision. The room should feel the clock and the ambiguity, not read a briefing.

## Voice

- Present tense, plain words, short sentences. "The help desk has six locked accounts" not "It has been observed that a number of accounts have experienced lockouts."
- Name the source of the news: who calls, what screen, which email. Real incidents arrive through people and tools.
- One fact the room did not have before, one decision it cannot avoid.
- Host lines are spoken. Write them to be read aloud in under 30 seconds and end them with a question to the room.

## Pacing

- Detection injects are ambiguous: the room should be able to argue it is nothing.
- Escalation injects make the cost of waiting visible.
- Containment injects put two good options against each other (stop the spread, keep the hospital running).
- Recovery injects reveal what was never tested (the backup, the restore order, the vendor contract).
- Notification injects start a clock and ask who owns it, today, by name.
- Every inject removes an option or raises the stakes. Never resolve the previous inject's tension for the room.

## Realism without invention

- Use the seed's asset names and CVE exactly. "vpngw01 is running a version with CVE-2025-0282" is real; "the Citrix farm" is invented if the seed never said Citrix.
- Use the plan's own words for roles and procedures: "Hospital Command Center", "SEV1", "Director of Infrastructure".
- Ambiguity is realistic; fabricated precision is not. "Several hundred records" is fine as texture; "48,213 records" is a number no tool returned.
- Conflicting information should come from two credible sources (vendor and forensics, help desk and SOC), not from a strawman.

## Examples

Weak:
> A ransomware attack has been detected. What do you do?

Strong:
> 02:10. The night charge nurse on 4 West calls the help desk: the medication cabinet screen shows a message demanding payment, and the EHR will not load on two workstations. The SOC sees the same file name appearing on dc1. Who is the first person you wake up, and what do you tell them?

Weak host line:
> Please discuss your containment strategy.

Strong host line:
> You can cut vpngw01 off right now. That also cuts every clinician working from home tonight. Who makes that call, and what do you say to the ones who lose access?

Weak "where teams fail":
> Teams may struggle with communication.

Strong:
> The team reimages the gateway before anyone takes a forensic image, so the report to the regulator cannot say when the attacker got in.

## Checklist per inject

- Under 70 words of `what_happens`; one `decision_forced` question
- Every system name traces to the seed or the plan
- The host line ends in a question to a named role
- `what_good_looks_like` cites the plan procedure the inject tests
- `where_teams_fail` is specific enough to score
