"""Set up Tabletop GM in a private .venv folder inside this download. Standard library only.

  python scripts/bootstrap.py            set up if needed, then open the launcher menu
  python scripts/bootstrap.py --setup    set up if needed and print the ttx command to use
  python scripts/bootstrap.py --check    report status only; change nothing

Safe to run any number of times: after the first run it only checks that the
installed version matches pyproject.toml. The first run needs internet access
to download the Python packages from PyPI.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import venv
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VENV = REPO / ".venv"
STAMP = VENV / ".tabletop-gm-installed"
MIN_PY = (3, 11)


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def ttx_command() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "ttx.exe"
    return VENV / "bin" / "ttx"


def _fingerprint() -> str:
    return hashlib.sha256((REPO / "pyproject.toml").read_bytes()).hexdigest()


def status() -> dict:
    return {
        "python_ok": sys.version_info[:2] >= MIN_PY,
        "python": sys.version.split()[0],
        "venv": VENV.exists() and venv_python().exists(),
        "installed": STAMP.exists() and STAMP.read_text(encoding="utf-8").strip() == _fingerprint() and ttx_command().exists(),
        "ttx": str(ttx_command()),
    }


def setup(quiet: bool = False) -> Path:
    if sys.version_info[:2] < MIN_PY:
        raise SystemExit(f"Tabletop GM needs Python {MIN_PY[0]}.{MIN_PY[1]} or newer; this is {sys.version.split()[0]}.")
    say = (lambda *a: None) if quiet else print
    st = status()
    if st["installed"]:
        return ttx_command()
    if not st["venv"]:
        say("First run: creating a private Python environment in .venv (about a minute)...")
        try:
            venv.EnvBuilder(with_pip=True, clear=False).create(VENV)
        except Exception as exc:  # most often: Debian/Ubuntu without the venv module
            raise SystemExit(
                f"Could not create the Python environment ({exc}).\n"
                "On Debian or Ubuntu, install the venv module first, for example: sudo apt install python3-venv"
            )
    say("Installing Tabletop GM and its document libraries from PyPI...")
    cmd = [str(venv_python()), "-m", "pip", "install", "--disable-pip-version-check", "-q", "-e", str(REPO) + "[dev]"]
    result = subprocess.run(cmd, cwd=REPO)
    if result.returncode != 0:
        raise SystemExit("Installation failed. Check your internet connection and run the launcher again.")
    STAMP.write_text(_fingerprint(), encoding="utf-8")
    say("Setup complete.")
    return ttx_command()


def main(argv: list[str]) -> int:
    if "--check" in argv:
        st = status()
        for k, v in st.items():
            print(f"{k}: {v}")
        return 0 if st["python_ok"] and st["installed"] else 1
    ttx = setup(quiet="--quiet" in argv)
    if "--setup" in argv:
        # the short form is what the project's permission rules pre-approve
        short = ".venv\\Scripts\\ttx.exe" if os.name == "nt" else ".venv/bin/ttx"
        print(f"ttx command (run from the repository root): {short}")
        return 0
    launcher = REPO / "scripts" / "launcher.py"
    return subprocess.run([str(venv_python()), str(launcher)] + [a for a in argv if a != "--quiet"], cwd=REPO).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
