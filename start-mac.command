#!/bin/bash
# Tabletop GM launcher for macOS. Double-click in Finder to run.
# The first time, macOS may say it is from an unidentified developer:
# right-click the file, choose Open, then Open again.
# First run: finds Python 3.11+ (offers Homebrew if you have it), creates a private
# .venv folder here, installs Tabletop GM, then shows the menu.
cd "$(dirname "$0")" || exit 1

ok() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; }

find_python() {
  # python.org and Homebrew installs first; the system python3 shim is often 3.9
  for p in /Library/Frameworks/Python.framework/Versions/3.1[1-9]/bin/python3 \
           /opt/homebrew/bin/python3.1[1-9] /opt/homebrew/bin/python3 \
           /usr/local/bin/python3.1[1-9] /usr/local/bin/python3; do
    [ -x "$p" ] && ok "$p" && { echo "$p"; return 0; }
  done
  for c in python3.13 python3.12 python3.11 python3; do
    command -v "$c" >/dev/null 2>&1 && ok "$c" && { echo "$c"; return 0; }
  done
  return 1
}

PY=$(find_python)
if [ -z "$PY" ]; then
  echo
  echo " Tabletop GM needs Python 3.11 or newer, and it is not installed."
  if command -v brew >/dev/null 2>&1; then
    read -r -p " Install Python 3.12 with Homebrew now? [Y/n] " answer
    case "$answer" in
      ""|y|Y|yes) brew install python@3.12 && PY=$(find_python) ;;
    esac
  fi
fi
if [ -z "$PY" ]; then
  echo
  echo " Install Python from https://www.python.org/downloads/ and double-click this file again."
  open "https://www.python.org/downloads/" 2>/dev/null
  read -r -p " Press Return to close. " _
  exit 1
fi

"$PY" scripts/bootstrap.py "$@"
status=$?
if [ $status -ne 0 ]; then
  echo
  read -r -p " Something went wrong (see above). Press Return to close. " _
fi
exit $status
