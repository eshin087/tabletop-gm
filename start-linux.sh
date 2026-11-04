#!/bin/bash
# Tabletop GM launcher for Linux. Run in a terminal:  ./start-linux.sh
# First run: finds Python 3.11+, creates a private .venv folder here, installs
# Tabletop GM, then shows the menu. Later runs go straight to the menu.
cd "$(dirname "$0")" || exit 1

ok() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; }

PY=""
for c in python3.13 python3.12 python3.11 python3 python; do
  if command -v "$c" >/dev/null 2>&1 && ok "$c"; then PY="$c"; break; fi
done

if [ -z "$PY" ]; then
  echo
  echo " Tabletop GM needs Python 3.11 or newer, and it is not installed."
  echo " Install it with your package manager, for example:"
  echo "   Debian or Ubuntu:  sudo apt install python3.12 python3.12-venv"
  echo "   Fedora:            sudo dnf install python3.12"
  echo " Then run ./start-linux.sh again."
  exit 1
fi

exec "$PY" scripts/bootstrap.py "$@"
