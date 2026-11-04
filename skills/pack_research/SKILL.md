---
name: pack_research
description: Research a sector's notification deadlines and exercise requirements from authoritative sources and draft an industry pack (pack.md, clocks.yaml, defaults.yaml) at the researched tier, so any industry can be supported. Never promotes a clock to verified.
---

# Pack research

Packs are how Tabletop GM supports an industry. Every deadline the engine uses comes from a pack's `clocks.yaml` or `clocks_common.yaml`. This skill drafts a pack for a sector that has none, or refreshes an existing one.

## Start from the template

Copy `skills/industry_packs/_template/` to `skills/industry_packs/<slug>/`. Keep every key, every heading, and the key order. Read one finished pack (`healthcare` or `banking`) before you start.

## Sources: authoritative only

Use, in order of preference: the regulation's official text (eCFR, Federal Register, EUR-Lex, legislation.gov.uk, state legislature sites), the regulator's own pages (sec.gov, hhs.gov, ftc.gov, dfs.ny.gov, state attorney general sites), and standards bodies (NIST, PCI SSC, ISA/IEC, NERC). Law firm and vendor summaries may help you find the rule; they are never the `source_url`.

Open every URL you record and confirm it contains the deadline language. If a site blocks automated fetching, a faithful mirror of the official text (for example law.cornell.edu for the CFR) may confirm the words; record the official URL as `source_url` and say in `notes` which mirror confirmed it. If you cannot open any copy, either leave the clock out or include it with `notes: "source not fetched; verify before use"`.

## Each clock

- `id`: snake_case, globally unique (prefix with the law or the pack)
- `deadline_hours` (calendar hours) or `deadline_business_days`, or both null with the rule's own words in `deadline_text` ("without unreasonable delay")
- `deadline_text`: the rule's words, quoted or closely paraphrased
- `trigger`: what starts the clock (discovery, determination, notice to individuals...)
- `after_clock`: when the deadline runs from another clock's notice rather than from the trigger
- `applies_when`: only `industries`, `data_types`, `countries`, `states`, `public_company`, `flags`, `min_affected`
- `tier: researched`, `verified_date` (today), `verifier: "pack_research skill (Claude), not yet human-checked"`

Clocks that many sectors share (GDPR, SEC 8-K, state breach laws, CIRCIA, card brands) belong in `clocks_common.yaml`, once.

## Never

- Never set `tier: verified`. A human promotes a clock after opening the source: `tier: verified`, `verifier: <their name>`, `verified_date: <the date they checked>`.
- Never invent a deadline, a citation, or a URL. A clock with no source link fails the build.
- Never name a real organization or breach victim in pack text.

## Finish

```
ttx validate packs
```

Zero errors. Then tell the person how many clocks you drafted, which ones you could not confirm, and that every output using them will carry the "verify before exercise" banner until someone promotes them.
