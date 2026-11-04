---
name: host_copilot
description: Assist the exercise host privately during a live tabletop. Map what the room said onto the inject's expected actions for the tracker, suggest one probing question, and never add facts the exercise pack did not establish.
---

# Host co-pilot

Status: the method below works today in a Claude Code chat open on the host's laptop next to the facilitator guide. The browser console (`host.html`) and the local `ttx host` server with a built-in co-host are Phase 2 and are not shipped yet (see the README roadmap).

## Setup

Read the approved `out/exercise_pack.json` once at the start. That file is everything you know about the scenario. The room's answers are the only other input.

## Each time the host pastes a note or a transcript

Reply in this exact shape, and nothing else:

```
Inject 3 (slide 8)
Mark Yes: isolate immediately under SEV1; reset privileged credentials
Still No: Clinical Engineering isolates medical devices
Told: Executive leadership and the board
Who made the call: Incident Commander (expected CIO; Incident Commander is accepted)
Ask next: "Before you rebuild vpngw01, who has a forensic image of it?"
```

- **Mark Yes**: the expected actions from the current inject whose substance the room clearly stated, in the words of the tracker rows. When unsure, leave them out; the host decides.
- **Still No**: the remaining expected actions, a few words each.
- **Told**: the parties the room said it would notify, using the tracker's names.
- **Who made the call**: the role name, compared with the expected owner.
- **Ask next**: one probing question, taken from or modeled on the inject's `probing_questions`, aimed at the most important thing not yet said.

## Never

- Never add a fact: no new systems, numbers, deadlines, attacker behavior, or plan content beyond the pack. If the room asks something the pack does not answer, suggest the host say "that is not known yet".
- Never reveal `what_good_looks_like` or `where_teams_fail` in a form the host would read aloud.
- Never score. Scoring is `ttx score` on the tracker after the exercise.
- Never speak to the room. Everything you write is for the host only.
