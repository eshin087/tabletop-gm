"""Notification clock engine.

Reads clocks.yaml from the selected industry pack(s), clocks_common.yaml, and
any clock from another pack whose required flags the intake sets. Evaluates
applies_when against the intake and returns the applicable clocks, each with
its source URL, verified date, and tier. With incident timestamps it computes
the deadline and whether a recorded notification met it.

No deadline ever comes from anywhere but the YAML.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .common import as_list, now_iso, parse_iso
from .packs import list_packs, load_common_clocks, load_pack

BANNER_TEXT = (
    "Verify before exercise: the following notification clocks were researched from "
    "primary sources but have not been human-verified: {ids}. Open each source URL and "
    "promote the clock in clocks.yaml (tier: verified) before relying on it."
)


def _intake_sets(intake: dict) -> dict[str, Any]:
    return {
        "industries": {str(intake.get("industry") or "").lower()} | {s.lower() for s in as_list(intake.get("additional_packs"))},
        "data_types": {str(d).upper() if str(d).upper() in {"PHI", "PII", "PCI", "PFI", "CUI", "OT", "SSN"} else str(d) for d in as_list(intake.get("data_types"))},
        "countries": {str(c).upper() for c in as_list(intake.get("countries"))},
        "states": {str(s).upper() for s in as_list(intake.get("states"))},
        "public_company": bool(intake.get("public_company", False)),
        "flags": {str(f).lower() for f in as_list(intake.get("regulated"))},
        "affected": int(intake.get("affected_estimate") or 0),
    }


def applies(clock: dict, intake: dict) -> tuple[bool, list[str]]:
    """Evaluate applies_when. Returns (applies, reasons)."""
    cond = clock.get("applies_when") or {}
    facts = _intake_sets(intake)
    reasons: list[str] = []
    if not cond:
        return True, ["no conditions"]
    if "industries" in cond:
        wanted = {str(i).lower() for i in as_list(cond["industries"])}
        if not (wanted & facts["industries"]):
            return False, [f"industry not in {sorted(wanted)}"]
        reasons.append(f"industry in {sorted(wanted)}")
    if "data_types" in cond:
        wanted = {str(d) for d in as_list(cond["data_types"])}
        hit = wanted & facts["data_types"]
        if not hit:
            return False, [f"data types {sorted(wanted)} not held"]
        reasons.append(f"holds {sorted(hit)}")
    if "countries" in cond:
        wanted = {str(c).upper() for c in as_list(cond["countries"])}
        hit = wanted & facts["countries"]
        if not hit:
            return False, [f"not operating in {sorted(wanted)}"]
        reasons.append(f"operates in {sorted(hit)}")
    if "states" in cond:
        wanted = {str(s).upper() for s in as_list(cond["states"])}
        hit = wanted & facts["states"]
        if not hit:
            return False, [f"not operating in states {sorted(wanted)}"]
        reasons.append(f"operates in {sorted(hit)}")
    if "public_company" in cond and cond["public_company"] is not None:
        if bool(cond["public_company"]) != facts["public_company"]:
            return False, ["public company status does not match"]
        reasons.append("public company" if facts["public_company"] else "private company")
    if "flags" in cond:
        wanted = {str(f).lower() for f in as_list(cond["flags"])}
        missing = wanted - facts["flags"]
        if missing:
            return False, [f"missing flags {sorted(missing)}"]
        reasons.append(f"flags {sorted(wanted)}")
    if "min_affected" in cond and cond["min_affected"] is not None:
        if facts["affected"] < int(cond["min_affected"]):
            return False, [f"affected estimate {facts['affected']} below {cond['min_affected']}"]
        reasons.append(f"affected estimate {facts['affected']} meets {cond['min_affected']}")
    return True, reasons


def candidate_clocks(intake: dict, packs_base=None) -> list[dict]:
    """All clocks that could apply: selected packs, common, and flag-matched clocks from other packs."""
    selected = [str(intake.get("industry") or "").lower()] + [s.lower() for s in as_list(intake.get("additional_packs"))]
    selected = [s for s in selected if s]
    out: list[dict] = []
    seen: set[str] = set()
    include_common = False
    available = list_packs(packs_base)
    for slug in selected:
        if slug not in available:
            raise FileNotFoundError(f"no industry pack named '{slug}'; available: {', '.join(available)}")
        pack = load_pack(slug, packs_base)
        include_common = include_common or pack.includes_common
        for c in pack.clocks:
            if c["id"] not in seen:
                out.append(c)
                seen.add(c["id"])
    if include_common or not selected:
        for c in load_common_clocks(packs_base):
            if c["id"] not in seen:
                out.append(c)
                seen.add(c["id"])
    flags = {str(f).lower() for f in as_list(intake.get("regulated"))}
    for slug in available:
        if slug in selected:
            continue
        for c in load_pack(slug, packs_base).clocks:
            need = {str(f).lower() for f in as_list((c.get("applies_when") or {}).get("flags"))}
            if need and need <= flags and c["id"] not in seen:
                out.append(c | {"loaded_because": f"flags {sorted(need)} set in intake"})
                seen.add(c["id"])
    return out


def add_business_days(start: datetime, days: int) -> datetime:
    """Business-day arithmetic that skips weekends. Holidays are not modeled; say so in outputs."""
    cur = start
    remaining = days
    while remaining > 0:
        cur = cur + timedelta(days=1)
        if cur.weekday() < 5:
            remaining -= 1
    return cur


def deadline_at(clock: dict, trigger_at: datetime | None) -> datetime | None:
    if trigger_at is None:
        return None
    if clock.get("deadline_hours") is not None:
        return trigger_at + timedelta(hours=float(clock["deadline_hours"]))
    if clock.get("deadline_business_days") is not None:
        return add_business_days(trigger_at, int(clock["deadline_business_days"]))
    return None


def _hours_between(a: datetime, b: datetime) -> float:
    return round((b - a).total_seconds() / 3600.0, 2)


def evaluate(intake: dict, incident: dict | None = None, packs_base=None) -> dict:
    """Return the applicable clocks for an intake.

    incident (optional): {"trigger_at": iso, "notifications": {clock_id: iso}}.
    trigger_at is the moment the organization discovered or determined the
    incident (the facilitator decides which, per clock trigger text).
    """
    incident = incident or {}
    trigger_at = parse_iso(incident.get("trigger_at"))
    notifications = incident.get("notifications") or {}
    applicable: list[dict] = []
    excluded: list[dict] = []
    for clock in candidate_clocks(intake, packs_base):
        ok, reasons = applies(clock, intake)
        if not ok:
            excluded.append({"id": clock["id"], "pack": clock.get("pack"), "reason": "; ".join(reasons)})
            continue
        entry = {
            "id": clock["id"],
            "pack": clock.get("pack"),
            "name": clock.get("name"),
            "regulator": clock.get("regulator"),
            "jurisdiction": clock.get("jurisdiction"),
            "trigger": clock.get("trigger"),
            "deadline_hours": clock.get("deadline_hours"),
            "deadline_business_days": clock.get("deadline_business_days"),
            "deadline_text": clock.get("deadline_text"),
            "source_url": clock.get("source_url"),
            "citation": clock.get("citation"),
            "tier": clock.get("tier"),
            "verified_date": str(clock.get("verified_date")) if clock.get("verified_date") is not None else None,
            "verifier": clock.get("verifier"),
            "notes": clock.get("notes"),
            "applies_because": reasons + ([clock["loaded_because"]] if clock.get("loaded_because") else []),
        }
        due = deadline_at(clock, trigger_at)
        if trigger_at is not None:
            entry["trigger_at"] = trigger_at.isoformat()
            entry["deadline_at"] = due.isoformat() if due else None
            notified = parse_iso(notifications.get(clock["id"]))
            if notified is not None:
                entry["notified_at"] = notified.isoformat()
                entry["hours_to_notify"] = _hours_between(trigger_at, notified)
                if due is not None:
                    entry["met"] = notified <= due
                    entry["margin_hours"] = _hours_between(notified, due)
                else:
                    entry["met"] = None
                    entry["margin_hours"] = None
            else:
                entry["notified_at"] = None
                entry["met"] = None
        applicable.append(entry)
    applicable.sort(key=lambda c: (_sort_hours(c), c["id"]))
    researched = [c["id"] for c in applicable if c.get("tier") != "verified"]
    missing_source = [c["id"] for c in applicable if not c.get("source_url")]
    return {
        "schema_version": "1",
        "generated_at": now_iso(),
        "intake_summary": {
            "industry": intake.get("industry"),
            "additional_packs": as_list(intake.get("additional_packs")),
            "countries": as_list(intake.get("countries")),
            "states": as_list(intake.get("states")),
            "data_types": as_list(intake.get("data_types")),
            "public_company": bool(intake.get("public_company", False)),
            "regulated": as_list(intake.get("regulated")),
            "affected_estimate": intake.get("affected_estimate"),
        },
        "clocks": applicable,
        "excluded": excluded,
        "researched_clock_ids": researched,
        "missing_source_ids": missing_source,
        "banner": {
            "show": bool(researched),
            "text": BANNER_TEXT.format(ids=", ".join(researched)) if researched else "",
        },
        "business_day_note": "Business-day deadlines skip weekends only; public holidays are not modeled.",
    }


def _sort_hours(c: dict) -> float:
    if c.get("deadline_hours") is not None:
        return float(c["deadline_hours"])
    if c.get("deadline_business_days") is not None:
        return float(c["deadline_business_days"]) * 24.0 * 1.4
    return 10**9


def shortest_clock(clocks_result: dict) -> dict | None:
    """The tightest clock with a numeric deadline, or None."""
    numeric = [c for c in clocks_result.get("clocks", []) if c.get("deadline_hours") is not None or c.get("deadline_business_days") is not None]
    if not numeric:
        return None
    return min(numeric, key=_sort_hours)
