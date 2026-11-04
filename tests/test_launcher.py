"""The launcher path a newcomer uses: bootstrap status, the demo choice, and the launch scripts."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_demo_choice_builds_everything(tmp_path):
    out = tmp_path / "demo"
    r = subprocess.run([sys.executable, "scripts/launcher.py", "--choice", "demo", "--no-open", "--out", str(out)],
                       cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    for name in ("START_HERE.txt", "deck.pptx", "facilitator_guide.docx", "participant_handout.docx", "decision_tracker.xlsx",
                 "decision_tracker_completed.xlsx", "attendance_signin.xlsx", "signoff_sheet.docx", "after_action_report.docx",
                 "exercise_pack.json", "score.json"):
        assert (out / name).exists(), name
    assert "scored" in r.stdout


def test_ttx_demo_command(tmp_path):
    r = subprocess.run([sys.executable, "-m", "ttx.cli", "demo", "--no-open", "--out", str(tmp_path / "d")],
                       cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "d" / "after_action_report.docx").exists()


def test_bootstrap_check_changes_nothing():
    before = (REPO / ".venv").exists()
    r = subprocess.run([sys.executable, "scripts/bootstrap.py", "--check"], cwd=REPO, capture_output=True, text=True)
    assert r.returncode in (0, 1)
    assert "python_ok: True" in r.stdout
    assert (REPO / ".venv").exists() == before


def test_launch_scripts_are_shipped_correctly():
    bat = (REPO / "start-windows.bat").read_bytes()
    assert b"\r\n" in bat and bat.count(b"\n") == bat.count(b"\r\n"), "the .bat must use CRLF line endings"
    for name in ("start-mac.command", "start-linux.sh"):
        data = (REPO / name).read_bytes()
        assert data.startswith(b"#!/bin/bash") and b"\r\n" not in data
    modes = subprocess.run(["git", "ls-files", "-s", "start-mac.command", "start-linux.sh"], cwd=REPO, capture_output=True, text=True).stdout
    if modes:  # inside a git checkout
        assert modes.count("100755") == 2


def test_unknown_launcher_choice_fails_cleanly():
    r = subprocess.run([sys.executable, "scripts/launcher.py", "--choice", "nope"], cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 2


def test_launcher_offers_the_live_choice():
    r = subprocess.run([sys.executable, "scripts/launcher.py", "--choice", "nope"], cwd=REPO, capture_output=True, text=True)
    assert "live" in r.stdout
    text = (REPO / "scripts" / "launcher.py").read_text(encoding="utf-8")
    assert "Run an exercise live in chat" in text and "Run an exercise live in this chat" in text
