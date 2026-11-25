"""Render the host console page. One self-contained file: no CDN, no fonts, no network.

The same page runs two ways. Served by ``ttx host`` it talks to the local
server, which records through the engine. Written by ``ttx build`` as
``host.html`` it runs from a double-click, keeps the log in the browser, and
exports ``decision_log.json`` for ``ttx report --log``.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import __version__

TEMPLATE = Path(__file__).with_name("console.html")
ROOM_TEMPLATE = Path(__file__).with_name("room.html")
MARKER = "__TTX_BOOT__"


def render_console(boot: dict, served: bool) -> str:
    data = dict(boot)
    data["served"] = bool(served)
    data.setdefault("version", __version__)
    blob = json.dumps(data, ensure_ascii=False, default=str)
    # The data sits inside a <script type="application/json"> block, so no "<" may survive as markup.
    blob = blob.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return TEMPLATE.read_text(encoding="utf-8").replace(MARKER, blob)


def render_room() -> str:
    """The room screen. It carries no data of its own: it asks the server for the spoiler-free room state."""
    return ROOM_TEMPLATE.read_text(encoding="utf-8")


def build_host_console(pack: dict, out_path: str | Path, draft: bool = False) -> Path:
    """Write the standalone host.html for an exercise pack."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    boot = {"pack": pack, "log": None, "report": None, "server": None, "token": None, "draft": bool(draft)}
    out.write_text(render_console(boot, served=False), encoding="utf-8", newline="\n")
    return out
