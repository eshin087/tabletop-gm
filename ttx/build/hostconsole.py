"""host.html: the standalone host console for a second laptop. No server, no network, no model.

The page itself lives in ``ttx/host/console.html`` and is shared with ``ttx host``.
"""

from __future__ import annotations

from ..host.console import build_host_console

__all__ = ["build_host_console"]
