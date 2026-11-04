"""Tabletop GM menu. Runs inside .venv (scripts/bootstrap.py starts it).

  1  See a finished sample exercise (no account, no internet)
  2  Build an exercise for my organization (opens Claude Code with /tabletop)

Non-interactive use (tests, scripts):  launcher.py --choice demo [--no-open]
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

CLAUDE_PROMPT = ("Use the tabletop skill (/tabletop) to build a cybersecurity tabletop exercise for my organization. "
                 "Start with the intake interview.")
INSTALL_HELP = """
Claude Code is not installed (or not on your PATH).

Option 2 uses Claude Code to interview you, read your plans, and write the scenario.
It needs a Claude account. To install it:
  Windows (PowerShell):   irm https://claude.ai/install.ps1 | iex
  macOS or Linux:         curl -fsSL https://claude.ai/install.sh | bash
  Setup guide:            https://code.claude.com/docs/en/setup
Then run this launcher again and choose 2.

Already use the Claude desktop app? Open this folder in its Code tab and type /tabletop.
Meanwhile, option 1 shows a complete sample exercise with no account needed.
"""

BANNER = r"""
  Tabletop GM
  Cybersecurity tabletop exercises built from your industry, your exposure data, and your own plans.
"""


def run_demo(open_after: bool = True, out: Path | None = None) -> int:
    from ttx.demo import open_folder, run_sample, write_guide

    out = Path(out) if out else REPO / "out" / "demo"
    print("\nBuilding the sample exercise (synthetic data; about 10 seconds)...")
    result = run_sample(out)
    guide = write_guide(out)
    print(f"\nDone. {result['headline']}")
    print(f"\nYour files are in: {out}")
    print(f"Start with {guide.name}, then open deck.pptx, facilitator_guide.docx, and after_action_report.docx.")
    if open_after and open_folder(out):
        print("The folder is open in a new window.")
    return 0


def run_claude() -> int:
    claude = shutil.which("claude")
    if not claude:
        print(INSTALL_HELP)
        return 1
    env = dict(os.environ)
    bindir = str(Path(sys.executable).parent)
    env["PATH"] = bindir + os.pathsep + env.get("PATH", "")  # so `ttx` resolves inside Claude Code
    print("\nStarting Claude Code in this folder. It will interview you, then build the exercise.")
    print("Nothing is built until you approve the outline. Type /exit to leave Claude Code.\n")
    return subprocess.run([claude, CLAUDE_PROMPT], cwd=REPO, env=env).returncode


def menu() -> int:
    print(BANNER)
    while True:
        print("  1  See a finished sample exercise (no account needed)")
        print("  2  Build an exercise for my organization (uses Claude Code)")
        print("  Q  Quit\n")
        choice = input("Choose 1, 2, or Q: ").strip().lower()
        if choice in {"1", "demo"}:
            run_demo()
        elif choice in {"2", "build"}:
            run_claude()
        elif choice in {"q", "quit", "exit", ""}:
            return 0
        else:
            print("Please type 1, 2, or Q.\n")
            continue
        print()


def main(argv: list[str]) -> int:
    if "--choice" in argv:
        choice = argv[argv.index("--choice") + 1]
        if choice == "demo":
            out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
            return run_demo(open_after="--no-open" not in argv, out=out)
        if choice == "build":
            return run_claude()
        print(f"unknown choice {choice}; use demo or build")
        return 2
    try:
        return menu()
    except (KeyboardInterrupt, EOFError):
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
