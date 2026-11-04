"""Shared helpers: paths, file IO, hashing, timestamps."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"


def packs_dir(override: str | os.PathLike | None = None) -> Path:
    """Locate the industry packs directory.

    Order: explicit override, TTX_PACKS_DIR, ./skills/industry_packs relative to the
    current directory, then the directory shipped next to this package.
    """
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override))
    env = os.environ.get("TTX_PACKS_DIR")
    if env:
        candidates.append(Path(env))
    candidates.append(Path.cwd() / "skills" / "industry_packs")
    candidates.append(REPO_ROOT / "skills" / "industry_packs")
    for c in candidates:
        if c.is_dir():
            return c
    raise FileNotFoundError(
        "industry packs directory not found; set TTX_PACKS_DIR or run from the repo root"
    )


def schemas_dir() -> Path:
    env = os.environ.get("TTX_SCHEMAS_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    if (Path.cwd() / "schemas").is_dir():
        return Path.cwd() / "schemas"
    return SCHEMAS_DIR


def read_json(path: str | os.PathLike) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _json_default(obj: Any):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, set):
        return sorted(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def write_json(path: str | os.PathLike, data: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=False, default=_json_default)
        fh.write("\n")


def json_roundtrip(data: Any) -> Any:
    """Return a copy with dates and paths turned into strings (what a file write would hold)."""
    return json.loads(json.dumps(data, default=_json_default))


def read_yaml(path: str | os.PathLike) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def read_text(path: str | os.PathLike) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def sha256_file(path: str | os.PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_hash(data: Any) -> str:
    """Stable hash of a JSON-serializable structure."""
    blob = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=_json_default)
    return sha256_text(blob)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def parse_iso(value: str | datetime | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def slugify(text: str) -> str:
    out = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "_":
            out.append("_")
    return "".join(out).strip("_") or "exercise"


def as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    if isinstance(value, str):
        parts = [p.strip() for p in value.replace(";", ",").split(",")]
        return [p for p in parts if p]
    return [value]
