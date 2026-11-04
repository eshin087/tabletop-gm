"""Synthetic responses for demos and pitches: fill a tracker for any approved exercise.

The answers live in samples/demo_responses/responses.yaml and use tokens
(owner, other, all_but_last, {entry}) instead of names, so they fit any
exercise. Everything produced from them is labeled as demo data.
"""

from __future__ import annotations

from pathlib import Path

from .common import REPO_ROOT, as_list, read_yaml

RESPONSES_FILE = REPO_ROOT / "samples" / "demo_responses" / "responses.yaml"
DEMO_TRACKER_NAME = "demo_tracker.xlsx"  # never matches the decision_tracker* pattern real reports search
DEMO_LABEL = "DEMO: synthetic responses"
DEMO_NOTE = ("These results come from invented answers (samples/demo_responses/responses.yaml), "
             "not from a real exercise. Use them to show what the reports look like; do not report them as findings.")


def load_responses(path: str | Path | None = None) -> dict:
    spec = read_yaml(path or RESPONSES_FILE) or {}
    if not isinstance(spec.get("slots"), dict):
        raise ValueError(f"{path or RESPONSES_FILE} has no 'slots' section")
    return spec


def _pick(items: list, how: str) -> list:
    items = list(items)
    if how == "all":
        return items
    if how == "all_but_last":
        return items[:-1] if len(items) > 1 else items
    if how == "half":
        return items[: max(1, len(items) // 2)] if items else []
    if how == "first":
        return items[:1]
    if how == "none":
        return []
    raise ValueError(f"unknown selection '{how}'; use all, all_but_last, half, first, or none")


def _role_ids(pack: dict) -> list[str]:
    return [r["id"] for r in pack.get("roles", [])]


def _resolve_role(pack: dict, inj: dict, token: str, prefer: list[str] | None = None) -> str:
    owner = inj.get("decision_owner_role")
    accepted = as_list(inj.get("acceptable_owner_roles"))
    if token == "owner":
        return owner
    if token == "alternate":
        return accepted[0] if accepted else owner
    if token == "other":
        for rid in list(prefer or []) + _role_ids(pack):
            if rid not in _role_ids(pack):
                continue
            if rid != owner and rid not in accepted:
                return rid
        return owner
    if token in _role_ids(pack):
        return token
    raise ValueError(f"unknown decided_by '{token}'; use owner, alternate, other, or a role id from the exercise")


def _role_name(pack: dict, role_id: str | None) -> str:
    return next((r.get("name") or r["id"] for r in pack.get("roles", []) if r["id"] == role_id), role_id or "")


def _fill_text(text: str, values: dict) -> str:
    class Safe(dict):
        def __missing__(self, key):
            return "{" + key + "}"
    return (text or "").format_map(Safe(values))


def demo_answers(pack: dict, spec: dict | None = None) -> tuple[dict, dict]:
    """Return (decisions by inject id, clocks by clock id) in fill_host_tracker's shape."""
    from .build.tracker import CLOCK_TIMING

    spec = spec or load_responses()
    slots = spec["slots"]
    prefer = as_list(spec.get("other_prefer"))
    seed = pack.get("seed") or {}
    systems = {
        "entry": (seed.get("entry") or {}).get("asset") or "the first affected system",
        "pivot": (seed.get("pivot") or {}).get("asset") or "the identity systems",
        "target": (seed.get("target") or {}).get("asset") or "the most sensitive system",
    }
    decisions: dict[str, dict] = {}
    for inj in pack.get("injects", []):
        s = slots.get(inj.get("slot")) or slots.get("default")
        if not s:
            continue
        decided = _resolve_role(pack, inj, s.get("decided_by", "owner"), prefer)
        values = {
            **systems,
            "owner": _role_name(pack, inj.get("decision_owner_role")),
            "alternate": _role_name(pack, _resolve_role(pack, inj, "alternate")),
            "other": _role_name(pack, _resolve_role(pack, inj, "other", prefer)),
        }
        decisions[inj["id"]] = {
            "decided_by": decided,
            "speed": s.get("speed", "Within 1 hour"),
            "discussion": str(s.get("discussion", "10")),
            "actions": _pick([a["id"] for a in inj.get("expected_actions", [])], s.get("actions", "all")),
            "notified": _pick(as_list(inj.get("expected_notifications")), s.get("notified", "all")),
            "plan_step": s.get("plan_step", "Yes"),
            "documented": s.get("documented", "Yes"),
            "decision": _fill_text(s.get("decision", ""), values),
            "notes": _fill_text(s.get("notes", ""), values),
        }

    clock_spec = spec.get("clocks") or {}
    pattern = as_list(clock_spec.get("pattern")) or ["on_time"]
    starter = next((j for j in pack.get("injects", []) if as_list((j.get("flags") or {}).get("starts_clock"))), None)
    owner_token = clock_spec.get("owner", "notification_owner")
    if owner_token == "notification_owner":
        clock_owner = (starter or {}).get("decision_owner_role") or (_role_ids(pack) or [None])[0]
    else:
        clock_owner = owner_token
    options = [(label, hours) for label, hours in CLOCK_TIMING.items() if hours is not None]
    clocks: dict[str, tuple[str, str]] = {}
    ordered = sorted(pack.get("clocks", []), key=lambda c: (c.get("deadline_hours") is None, c.get("deadline_hours") or 0, c["id"]))
    for i, c in enumerate(ordered):
        how = pattern[i % len(pattern)]
        limit = c.get("deadline_hours")
        if how == "not_planned":
            continue
        if limit is None:
            clocks[c["id"]] = (clock_owner, "Within 30 days")
        elif how == "late":
            later = [lab for lab, h in options if h > limit]
            clocks[c["id"]] = (clock_owner, later[0] if later else options[-1][0])
        elif how == "on_time":
            inside = [lab for lab, h in options if h < limit] or [lab for lab, h in options if h <= limit]
            clocks[c["id"]] = (clock_owner, inside[-1] if inside else options[0][0])
        else:
            raise ValueError(f"unknown clock pattern '{how}'; use on_time, late, or not_planned")
    return decisions, clocks


def make_demo_tracker(pack: dict, out_dir: str | Path, spec_path: str | Path | None = None) -> Path:
    """Build the exercise's tracker and fill it with the synthetic answers. Returns its path."""
    from .build.tracker import build_tracker, fill_host_tracker

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / DEMO_TRACKER_NAME
    build_tracker(pack, path)
    decisions, clocks = demo_answers(pack, load_responses(spec_path))
    return fill_host_tracker(path, pack, decisions, clocks, out_path=path)
