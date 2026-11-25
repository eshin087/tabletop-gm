"""Deterministic check of anything the AI co-host writes. No model, no network.

The co-host is only allowed to speak from the approved exercise pack. This
module checks the three things code can check exactly:

  unknown_number  a number or an identifier containing a digit (a hostname, a
                  CVE, a finding ID, a score) that appears nowhere in the pack
  time_claim      a duration such as "48 hours" or "fifteen days" that the pack
                  does not contain, as written or derived from a pack deadline
  spoiler         five consecutive words lifted from an inject the room has not
                  reached, or from any inject's expected answer

A name with no digit in it (a vendor, a person) is not checked. That limit is
stated in the README; the host still reads every line before saying it.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

UNITS = ("minute", "hour", "day", "week", "month", "year")
_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45, "fifty": 50,
    "sixty": 60, "seventy": 70, "seventy-two": 72, "eighty": 80, "ninety": 90, "twenty-four": 24, "thirty-six": 36,
    "forty-eight": 48,
}
_NUM = r"\d+(?:\.\d+)?"
_WORD_ALT = "|".join(sorted((re.escape(w) for w in _WORDS), key=len, reverse=True))
_TIME_RE = re.compile(rf"\b({_NUM}|{_WORD_ALT})[\s-]+(business[\s-]+|calendar[\s-]+)?({'|'.join(UNITS)})s?\b", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-\.\+:/]*")
SPOILER_FIELDS_ANY = ("what_good_looks_like", "where_teams_fail")
SPOILER_FIELDS_LATER = ("title", "what_happens", "decision_forced", "host_lines", "probing_questions", "hints")
SHINGLE = 5


def _walk(value: Any) -> Iterable[Any]:
    if isinstance(value, dict):
        for v in value.values():
            yield from _walk(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _walk(v)
    else:
        yield value


def _plain_numbers(text: str) -> str:
    """Drop thousands separators so "3,200" is one number."""
    return re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)


def _digit_tokens(text: str) -> set[str]:
    out = set()
    for tok in _TOKEN_RE.findall(_plain_numbers(text)):
        tok = tok.strip(".,:;/-+").lower()
        if any(ch.isdigit() for ch in tok):
            out.add(tok)
            # "T+1:00" and "sql2016's" style: also keep the pieces around punctuation
            out.update(p for p in re.split(r"[^a-z0-9\.]+", tok) if any(ch.isdigit() for ch in p))
    return out


def _num(value: float) -> str:
    return f"{value:g}"


def _time_pairs(text: str) -> set[tuple[str, str]]:
    pairs = set()
    for qty, qualifier, unit in _TIME_RE.findall(text):
        q = qty.lower()
        n = _num(float(_WORDS[q])) if q in _WORDS else _num(float(q))
        pairs.add((n, unit.lower()))
    return pairs


def _derived_pairs(minutes: float | None = None, hours: float | None = None, days: float | None = None) -> set[tuple[str, str]]:
    """Every whole-number way to say one pack duration, so "60 days" matches a 1440 hour deadline."""
    total = None
    if minutes is not None:
        total = float(minutes)
    elif hours is not None:
        total = float(hours) * 60
    elif days is not None:
        total = float(days) * 1440
    if total is None:
        return set()
    out = set()
    for unit, size in (("minute", 1), ("hour", 60), ("day", 1440), ("week", 10080)):
        q = total / size
        if q >= 1 and abs(q - round(q)) < 1e-9:
            out.add((_num(round(q)), unit))
    return out


class Corpus:
    """What the pack establishes: its digit-bearing tokens and its durations."""

    def __init__(self, pack: dict, extra: Any = None):
        self.tokens: set[str] = set()
        self.pairs: set[tuple[str, str]] = set()
        for source in (pack, extra):
            if source is None:
                continue
            for leaf in _walk(source):
                if isinstance(leaf, bool) or leaf is None:
                    continue
                if isinstance(leaf, (int, float)):
                    self.tokens.add(_num(float(leaf)))
                else:
                    text = str(leaf)
                    self.tokens |= _digit_tokens(text)
                    self.pairs |= _time_pairs(text)
        for clock in pack.get("clocks", []) or []:
            if clock.get("deadline_hours") is not None:
                self.pairs |= _derived_pairs(hours=clock["deadline_hours"])
            if clock.get("deadline_business_days") is not None:
                self.pairs |= _derived_pairs(days=clock["deadline_business_days"])
        for inj in pack.get("injects", []) or []:
            if inj.get("plan_commitment_minutes") is not None:
                self.pairs |= _derived_pairs(minutes=inj["plan_commitment_minutes"])
            for action in inj.get("expected_actions", []) or []:
                if action.get("timing_minutes") is not None:
                    self.pairs |= _derived_pairs(minutes=action["timing_minutes"])
        for item in (pack.get("org_plan") or {}).get("items", []) or []:
            if item.get("internal_deadline_hours") is not None:
                self.pairs |= _derived_pairs(hours=item["internal_deadline_hours"])
        self.tokens |= {n for n, _unit in self.pairs}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _shingles(text: str) -> set[tuple[str, ...]]:
    w = _words(text)
    return {tuple(w[i:i + SHINGLE]) for i in range(len(w) - SHINGLE + 1)}


def _field_text(inj: dict, fields: Iterable[str]) -> str:
    parts = []
    for f in fields:
        v = inj.get(f)
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
        elif v:
            parts.append(str(v))
    return "\n".join(parts)


def spoiler_shingles(pack: dict, current_index: int | None) -> set[tuple[str, ...]]:
    """Word runs the co-host must not use yet. current_index None means nothing is off limits (the recap)."""
    if current_index is None:
        return set()
    injects = pack.get("injects", []) or []
    forbidden: set[tuple[str, ...]] = set()
    allowed: set[tuple[str, ...]] = set()
    for i, inj in enumerate(injects):
        forbidden |= _shingles(_field_text(inj, SPOILER_FIELDS_ANY))
        if i > current_index:
            forbidden |= _shingles(_field_text(inj, SPOILER_FIELDS_LATER))
        else:
            allowed |= _shingles(_field_text(inj, SPOILER_FIELDS_LATER))
            allowed |= _shingles(str((inj.get("procedure_tested") or {}).get("quote") or ""))
    return forbidden - allowed


def check_text(text: str, pack: dict, current_index: int | None = None, extra: Any = None, corpus: Corpus | None = None) -> list[dict]:
    """Return the findings for one piece of co-host text. An empty list means nothing checkable was invented."""
    corpus = corpus or Corpus(pack, extra)
    text = _plain_numbers(text)
    findings: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, token: str) -> None:
        if (kind, token) not in seen:
            seen.add((kind, token))
            findings.append({"kind": kind, "token": token})

    time_spans = []
    for m in _TIME_RE.finditer(text):
        qty, unit = m.group(1).lower(), m.group(3).lower()
        n = _num(float(_WORDS[qty])) if qty in _WORDS else _num(float(qty))
        time_spans.append(m.span())
        if (n, unit) not in corpus.pairs:
            add("time_claim", m.group(0))
    for m in _TOKEN_RE.finditer(text):
        tok = m.group(0).strip(".,:;/-+").lower()
        if not any(ch.isdigit() for ch in tok):
            continue
        if any(s <= m.start() < e for s, e in time_spans):
            continue  # already judged as a duration
        pieces = [p for p in re.split(r"[^a-z0-9\.]+", tok) if any(ch.isdigit() for ch in p)]
        if tok in corpus.tokens or (pieces and all(p in corpus.tokens for p in pieces)):
            continue
        add("unknown_number", m.group(0).strip(".,:;"))
    forbidden = spoiler_shingles(pack, current_index)
    if forbidden:
        for sh in _shingles(text):
            if sh in forbidden:
                add("spoiler", " ".join(sh))
                break
    return findings


def summarize(findings: list[dict]) -> str:
    if not findings:
        return "nothing outside the exercise pack"
    return "; ".join(f"{f['kind'].replace('_', ' ')}: {f['token']}" for f in findings)
