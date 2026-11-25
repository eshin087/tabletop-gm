"""The optional AI co-host for ``ttx host``. Needs the ``anthropic`` package and ANTHROPIC_API_KEY.

Two jobs, both private to the host's screen:

  suggest   map the room's one-sentence answer onto the inject's own ids (deciding
            role, expected actions, parties notified) and pick one of the inject's
            probing questions. The answer is constrained to those ids by a JSON
            schema, and the host confirms before anything is logged.
  voice     stream a short line the host can read aloud: the inject reworded to
            follow the last decision, or a labeled stakeholder line that presses
            for the decision already posed.

The co-host is never shown an inject the room has not reached, and never an
expected answer when it writes a line for the room. ``ttx.host.conduct`` checks
every line it writes. Without a key the console runs from the pack's own script.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Iterator

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
# USD per million tokens (input, output, cache read, 5-minute cache write), list prices checked 2026-11-24.
# Haiku 5.5 is priced for prompts of 100K tokens or fewer, which every co-host request is.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    "claude-sonnet-5-5": (2.00, 10.00, 0.10, 2.50),
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
}
# Models that accept speed="fast". Asking for fast mode on any other model is ignored.
FAST_MODELS = ("claude-opus-5-5", "claude-opus-5", "claude-opus-4-8", "claude-fable-5-2")
# Models with no server-side fallback: the fallbacks parameter is left off their requests.
NO_FALLBACK = ("claude-haiku-5-5",)
FAST_MULTIPLIER = 2.0

VOICE_RULES = """You are the co-host for a live cybersecurity tabletop exercise. This is a defensive training exercise: \
a leadership team practices its own incident response plan against a fictional scenario. You write short lines that the \
human host reads on a private screen and may read aloud to the room.

Rules that hold in every line:
- Use only the exercise facts given in this conversation. Never add a system, a finding, a number, a deadline, a duration, \
an attacker action, or plan content that is not in those facts. When in doubt, leave it out.
- Never hint at what happens next, what a good answer would be, or how the room is doing. Acknowledge and move on.
- Never state a clock time. The engine keeps time.
- If the room asks "what if", the answer is: That's not known to you yet.
- If the room asks for information the facts do not hold, the answer is: You'd have to find that out. Who would you ask?
- Plain spoken words a room can follow. No markdown, no lists, no headings, no preamble about what you are doing."""

SUGGEST_RULES = """You help the host of a live cybersecurity tabletop exercise keep an accurate record. The host typed \
what the room decided. Map it onto the ids you are given, for the host to confirm before it is logged.

- Mark an expected action as completed only when the room clearly stated its substance. When unsure, leave it out.
- List a party as notified only when the room said it would tell them.
- decided_by_role is the role that made the call, or "unclear" when the note does not say.
- plan_step_followed and documented are "unclear" unless the note says.
- unplanned is true only when the room did something reasonable that does not answer the decision the inject poses.
- decision restates the room's decision in one sentence in their own terms. Add no fact the note does not contain.
- ask_next is the one probing question from the list that targets the most important thing the room has not said, \
or an empty string when nothing important is open."""


class CohostError(RuntimeError):
    """The co-host could not answer. The console falls back to the pack's own script."""


def _api_errors() -> tuple:
    """The SDK's error base class, or nothing when the optional package is absent (tests use a stand-in client)."""
    try:
        import anthropic
    except ImportError:
        return ()
    return (anthropic.APIError,)


def estimate_cost(usage: dict, model: str, fast: bool = False) -> float | None:
    price = PRICES.get(model)
    if not price:
        return None
    inp, out, cache_read, cache_write = price
    cost = (usage.get("input_tokens", 0) * inp + usage.get("output_tokens", 0) * out
            + usage.get("cache_read_input_tokens", 0) * cache_read
            + usage.get("cache_creation_input_tokens", 0) * cache_write) / 1_000_000
    return round(cost * (FAST_MULTIPLIER if fast else 1.0), 4)


def exercise_frame(pack: dict) -> dict:
    """The facts every call may use: the organization, the scenario, the roles, the parties, and the path."""
    seed = pack.get("seed") or {}
    path = {}
    for step in ("entry", "pivot", "target"):
        s = seed.get(step) or {}
        path[step] = {k: s.get(k) for k in ("asset", "finding_id", "cve", "plugin_name", "data") if s.get(k) is not None}
    scenario = pack.get("scenario") or {}
    return {
        "organization": (pack.get("organization") or {}).get("name"),
        "organization_description": (pack.get("organization") or {}).get("description"),
        "exercise_title": pack.get("title"),
        "scenario_family": scenario.get("family"),
        "severity_level": pack.get("severity_level"),
        "roles": [{"id": r["id"], "name": r.get("name")} for r in pack.get("roles", [])],
        "notify_parties": [{"id": p["id"], "name": p.get("name")} for p in pack.get("notify_parties", [])],
        "attack_path": path,
        "ground_rules": pack.get("ground_rules", []),
    }


def _role_name(pack: dict, role_id: str | None) -> str | None:
    for r in pack.get("roles", []):
        if r["id"] == role_id:
            return r.get("name") or role_id
    return role_id


def voice_facts(pack: dict, inject: dict) -> dict:
    """What a line for the room may draw on. No expected answers, nothing from a later inject."""
    proc = inject.get("procedure_tested") or {}
    return {
        "scenario_time": inject.get("time_marker"),
        "title": inject.get("title"),
        "what_happens": inject.get("what_happens"),
        "who_receives_it": inject.get("recipients"),
        "decision_forced": inject.get("decision_forced"),
        "decision_owner": _role_name(pack, inject.get("decision_owner_role")),
        "host_lines_from_the_script": inject.get("host_lines"),
        "probing_questions": inject.get("probing_questions"),
        "plan_section_tested": {"label": proc.get("label"), "quote": proc.get("quote")},
    }


def suggest_schema(pack: dict, inject: dict) -> dict:
    roles = [r["id"] for r in pack.get("roles", [])] + ["other", "unclear"]
    actions = [a["id"] for a in inject.get("expected_actions", [])]
    parties = [p["id"] for p in pack.get("notify_parties", [])]
    questions = list(inject.get("probing_questions") or []) + [""]
    props: dict[str, Any] = {
        "decision": {"type": "string"},
        "decided_by_role": {"type": "string", "enum": roles},
        "plan_step_followed": {"type": "string", "enum": ["yes", "partial", "no", "plan_unclear", "n/a", "unclear"]},
        "documented": {"type": "string", "enum": ["yes", "partial", "no", "unclear"]},
        "unplanned": {"type": "boolean"},
        "ask_next": {"type": "string", "enum": questions},
    }
    if actions:
        props["actions_completed"] = {"type": "array", "items": {"type": "string", "enum": actions}}
    if parties:
        props["notified"] = {"type": "array", "items": {"type": "string", "enum": parties}}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def clean_suggestion(raw: dict, pack: dict, inject: dict) -> dict:
    """Keep only ids the pack defines. The schema already constrains them; this is the engine's own check."""
    roles = {r["id"] for r in pack.get("roles", [])} | {"other"}
    actions = [a["id"] for a in inject.get("expected_actions", [])]
    parties = [p["id"] for p in pack.get("notify_parties", [])]
    questions = list(inject.get("probing_questions") or [])
    role = raw.get("decided_by_role")
    plan = raw.get("plan_step_followed")
    doc = raw.get("documented")
    return {
        "decision": str(raw.get("decision") or "").strip(),
        "decided_by_role": role if role in roles else None,
        "actions_completed": [a for a in actions if a in set(raw.get("actions_completed") or [])],
        "notified": [p for p in parties if p in set(raw.get("notified") or [])],
        "plan_step_followed": plan if plan in ("yes", "partial", "no", "plan_unclear", "n/a") else None,
        "documented": doc if doc in ("yes", "partial", "no") else None,
        "unplanned": bool(raw.get("unplanned")),
        "ask_next": raw.get("ask_next") if raw.get("ask_next") in questions else "",
    }


class AnthropicCohost:
    """Calls Claude through the official SDK. One instance per server; safe to call from request threads."""

    def __init__(self, client: Any = None, model: str | None = None, effort: str | None = None, fast: bool | None = None):
        if client is None:
            import anthropic  # optional dependency: pip install "tabletop-gm[host]"

            client = anthropic.Anthropic()
        self.client = client
        self.model = model or os.environ.get("TTX_HOST_MODEL") or DEFAULT_MODEL
        effort = (effort or os.environ.get("TTX_HOST_EFFORT") or "low").lower()
        self.effort = effort if effort in EFFORTS else "low"
        self.fast = bool(fast) if fast is not None else os.environ.get("TTX_HOST_FAST", "") in ("1", "true", "yes")
        self.fast = self.fast and self.model in FAST_MODELS
        self.usage = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "calls": 0}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #

    def info(self) -> dict:
        with self._lock:
            usage = dict(self.usage)
        return {"enabled": True, "model": self.model, "effort": self.effort, "fast": self.fast, "usage": usage,
                "estimated_cost_usd": estimate_cost(usage, self.model, self.fast)}

    def _count(self, usage: Any) -> None:
        if usage is None:
            return
        with self._lock:
            self.usage["calls"] += 1
            for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                self.usage[key] += int(getattr(usage, key, 0) or 0)

    def _request(self, rules: str, pack: dict, user: str, max_tokens: int, output_format: dict | None = None) -> dict:
        system = [
            {"type": "text", "text": rules},
            # The frame is the same for the whole session, so it is cached after the first call.
            {"type": "text", "text": "Exercise frame (facts you may use):\n" + json.dumps(exercise_frame(pack), indent=1, sort_keys=True),
             "cache_control": {"type": "ephemeral"}},
        ]
        output_config: dict[str, Any] = {"effort": self.effort}
        if output_format:
            output_config["format"] = output_format
        kwargs: dict[str, Any] = {
            "model": self.model, "max_tokens": max_tokens, "system": system,
            "messages": [{"role": "user", "content": user}],
            "output_config": output_config,
        }
        if self.model not in NO_FALLBACK:
            # A security exercise can trip a safety classifier by mistake. The fallback retries a declined
            # request on the model Anthropic recommends, inside the same call.
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        if self.fast:
            kwargs["speed"] = "fast"
        return kwargs

    @staticmethod
    def _wrap(exc: Exception) -> CohostError:
        import anthropic  # only reached for an SDK error, so the package is present

        if isinstance(exc, anthropic.AuthenticationError):
            return CohostError("the API key was rejected; check ANTHROPIC_API_KEY in .env")
        if isinstance(exc, anthropic.RateLimitError):
            return CohostError("the API rate limit was reached; wait a moment and ask again")
        if isinstance(exc, anthropic.APIStatusError):
            detail = str(getattr(exc, "message", "") or "")[:200]
            return CohostError(f"the API returned an error ({exc.status_code})" + (f": {detail}" if detail else ""))
        if isinstance(exc, anthropic.APIConnectionError):
            return CohostError("could not reach the API; check the network")
        return CohostError(f"co-host error: {exc.__class__.__name__}")

    # ------------------------------------------------------------------ #

    def suggest(self, pack: dict, inject: dict, room_text: str) -> dict:
        facts = {
            "inject_id": inject["id"], "title": inject.get("title"), "decision_forced": inject.get("decision_forced"),
            "expected_owner_role": inject.get("decision_owner_role"),
            "acceptable_owner_roles": inject.get("acceptable_owner_roles"),
            "expected_actions": [{"id": a["id"], "text": a.get("text")} for a in inject.get("expected_actions", [])],
            "expected_notifications": inject.get("expected_notifications"),
            "probing_questions": inject.get("probing_questions"),
        }
        user = ("Current inject:\n" + json.dumps(facts, indent=1) + "\n\nWhat the host typed for the room's decision:\n" + room_text.strip())
        kwargs = self._request(SUGGEST_RULES, pack, user, max_tokens=4000,
                               output_format={"type": "json_schema", "schema": suggest_schema(pack, inject)})
        try:
            response = self.client.beta.messages.create(**kwargs)
        except _api_errors() as exc:
            raise self._wrap(exc) from exc
        self._count(getattr(response, "usage", None))
        if response.stop_reason == "refusal":
            raise CohostError("the model declined this request; tick the boxes by hand")
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            raw = json.loads(text)
        except ValueError as exc:
            raise CohostError("the co-host's answer was cut short; tick the boxes by hand") from exc
        return clean_suggestion(raw, pack, inject)

    def voice(self, pack: dict, inject: dict, mode: str, room_text: str = "", earlier: list[dict] | None = None) -> Iterator[str]:
        """Yield the line as it is written. Raises CohostError on a refusal or an API failure."""
        facts = voice_facts(pack, inject)
        recap = [{"inject": e.get("title"), "decision": e.get("decision"), "decided_by": e.get("decided_by")} for e in (earlier or [])]
        if mode == "push":
            ask = ("The room has gone quiet. Write the one line a stakeholder would say to press for this decision. Use exactly this "
                   "form and nothing else: the role name as it appears in the roles list, a colon, then one or two sentences in "
                   "double quotes. The stakeholder may only refer to facts given above.")
        elif mode == "present":
            ask = ("Write how the host presents this inject to the room: two to four sentences that follow on from what the room "
                   "already decided, with every fact, name, and number unchanged, ending with the decision it forces, addressed to "
                   "the decision owner by role name.")
        else:
            ask = ("The room answered. Write at most three short sentences for the host: acknowledge the decision in a few words "
                   "without judging it, then press for whatever is still open. You may speak one line as a stakeholder, written as "
                   "the role name from the roles list, a colon, and the line in quotes, and you may ask one of the probing questions "
                   "as written. If nothing is open, a few words of acknowledgment are enough.")
        user = ("Current inject:\n" + json.dumps(facts, indent=1) + "\n\nWhat the room has decided so far:\n" + json.dumps(recap, indent=1)
                + (("\n\nThe room's answer to this inject:\n" + room_text.strip()) if room_text.strip() else "") + "\n\n" + ask)
        kwargs = self._request(VOICE_RULES, pack, user, max_tokens=4000)
        try:
            with self.client.beta.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    if text:
                        yield text
                final = stream.get_final_message()
        except _api_errors() as exc:
            raise self._wrap(exc) from exc
        self._count(getattr(final, "usage", None))
        if final.stop_reason == "refusal":
            # A decline can arrive after some text has streamed; that partial text must not be used.
            raise CohostError("the model declined this line; read the script instead")


def make_cohost(env: dict | None = None) -> tuple[AnthropicCohost | None, str]:
    """Return (cohost, reason). cohost is None when the AI parts are off, and reason says why in plain words."""
    env = os.environ if env is None else env
    if env.get("TTX_HOST_AI", "").lower() in ("0", "off", "false", "no"):
        return None, "the AI co-host is turned off (TTX_HOST_AI=off)"
    if not (env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN")):
        return None, "no ANTHROPIC_API_KEY in .env, so the console runs from the pack's script"
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return None, 'the anthropic package is not installed; run: pip install "tabletop-gm[host]"'
    return AnthropicCohost(), "AI co-host on"
