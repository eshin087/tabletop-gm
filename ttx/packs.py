"""Industry pack loading.

A pack is a folder under skills/industry_packs/<slug>/ with pack.md (story
material), clocks.yaml (deadlines and exercise requirements), and
defaults.yaml (roles, notify parties, expected actions used when no org plan
is uploaded). clocks_common.yaml holds clocks shared by many packs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .common import packs_dir, read_text, read_yaml

COMMON_FILE = "clocks_common.yaml"
REQUIRED_PACK_HEADINGS = [
    "## Who this pack is for",
    "## Typical scenarios",
    "## Stakeholders and roles",
    "## Hardest decisions",
    "## Notification clocks",
    "## Exercise requirements",
    "## Sector vocabulary",
    "## Sources",
]


@dataclass
class Pack:
    slug: str
    path: Path
    display_name: str = ""
    clocks: list[dict] = field(default_factory=list)
    exercise_requirements: list[dict] = field(default_factory=list)
    defaults: dict = field(default_factory=dict)
    markdown: str = ""
    includes_common: bool = True
    raw_clocks: dict = field(default_factory=dict)

    @property
    def roles(self) -> list[dict]:
        return list(self.defaults.get("roles") or [])

    @property
    def notify_parties(self) -> list[dict]:
        return list(self.defaults.get("notify_parties") or [])

    @property
    def expected_actions(self) -> dict[str, list[dict]]:
        return dict(self.defaults.get("expected_actions") or {})


def list_packs(base: str | Path | None = None) -> list[str]:
    root = packs_dir(base)
    slugs = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and not child.name.startswith("_") and (child / "clocks.yaml").exists():
            slugs.append(child.name)
    return slugs


def load_pack(slug: str, base: str | Path | None = None) -> Pack:
    root = packs_dir(base)
    path = root / slug
    if not (path / "clocks.yaml").exists():
        raise FileNotFoundError(f"pack '{slug}' not found under {root}")
    raw = read_yaml(path / "clocks.yaml") or {}
    defaults = read_yaml(path / "defaults.yaml") if (path / "defaults.yaml").exists() else {}
    markdown = read_text(path / "pack.md") if (path / "pack.md").exists() else ""
    clocks = []
    for clock in raw.get("clocks") or []:
        c = dict(clock)
        c["pack"] = slug
        clocks.append(c)
    reqs = []
    for req in raw.get("exercise_requirements") or []:
        r = dict(req)
        r["pack"] = slug
        reqs.append(r)
    return Pack(
        slug=slug,
        path=path,
        display_name=raw.get("display_name") or slug,
        clocks=clocks,
        exercise_requirements=reqs,
        defaults=defaults or {},
        markdown=markdown,
        includes_common=bool(raw.get("includes_common", True)),
        raw_clocks=raw,
    )


def load_common_clocks(base: str | Path | None = None) -> list[dict]:
    root = packs_dir(base)
    path = root / COMMON_FILE
    if not path.exists():
        return []
    raw = read_yaml(path) or {}
    out = []
    for clock in raw.get("clocks") or []:
        c = dict(clock)
        c["pack"] = "common"
        out.append(c)
    return out


def load_all_clocks(base: str | Path | None = None) -> list[dict]:
    """Every clock from every pack plus the common file."""
    out: list[dict] = []
    for slug in list_packs(base):
        out.extend(load_pack(slug, base).clocks)
    out.extend(load_common_clocks(base))
    return out


def pack_markdown_sections(markdown: str) -> dict[str, str]:
    """Split pack.md into {heading: body} for the top-level '## ' headings."""
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = line.strip()
            buf = []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def pack_summary(pack: Pack) -> dict[str, Any]:
    return {
        "slug": pack.slug,
        "display_name": pack.display_name,
        "clocks": len(pack.clocks),
        "researched_clocks": sum(1 for c in pack.clocks if c.get("tier") != "verified"),
        "exercise_requirements": len(pack.exercise_requirements),
        "roles": len(pack.roles),
    }
