"""End-to-end CLI run on the samples with no network, no keys, no model."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def run(*args, cwd=REPO):
    env = dict(os.environ)
    env.pop("TENABLE_ACCESS_KEY", None)
    env.pop("TENABLE_SECRET_KEY", None)
    env.pop("ANTHROPIC_API_KEY", None)
    proc = subprocess.run([sys.executable, "-m", "ttx.cli", *args], cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8")
    return proc


def test_prep_pipeline_end_to_end(tmp_path):
    out = tmp_path
    r = run("packs")
    assert r.returncode == 0 and "healthcare" in r.stdout

    r = run("ingest-plan", "samples/sample_ir_plan.md", "--out", str(out / "plan_text.json"))
    assert r.returncode == 0, r.stderr

    r = run("validate", "org-plan", "samples/org_plan_sample.json", "--plan-text", str(out / "plan_text.json"))
    assert r.returncode == 0, r.stdout + r.stderr

    r = run("seed", "--intake", "samples/intake_valley_regional.yaml", "--out", str(out / "seed.json"))
    assert r.returncode == 0, r.stdout + r.stderr
    seed = json.loads((out / "seed.json").read_text(encoding="utf-8"))
    assert seed["entry"]["asset"] == "vpngw01"

    r = run("clocks", "--intake", "samples/intake_valley_regional.yaml", "--out", str(out / "clocks.json"))
    assert r.returncode == 0, r.stdout + r.stderr
    clocks = json.loads((out / "clocks.json").read_text(encoding="utf-8"))
    assert any(c["id"] == "hipaa_individual_notice" for c in clocks["clocks"])

    r = run("outline", "--intake", "samples/intake_valley_regional.yaml", "--seed", str(out / "seed.json"),
            "--clocks", str(out / "clocks.json"), "--org-plan", "samples/org_plan_sample.json", "--out", str(out / "draft.json"))
    assert r.returncode == 0, r.stdout + r.stderr

    # the gate: building an unapproved outline is refused
    r = run("build", str(out / "draft.json"), "--out", str(out / "built"))
    assert r.returncode != 0
    assert "not approved" in (r.stdout + r.stderr)

    r = run("approve", str(out / "draft.json"), "--by", "Test Approver")
    assert r.returncode == 0, r.stdout + r.stderr

    r = run("validate", "exercise-pack", str(out / "draft.json"))
    assert r.returncode == 0, r.stdout + r.stderr

    r = run("build", str(out / "draft.json"), "--out", str(out / "built"))
    assert r.returncode == 0, r.stdout + r.stderr
    built = {p.suffix for p in (out / "built").iterdir()}
    assert {".pptx", ".docx", ".xlsx"} <= built


def test_seed_export_mode_from_cli(tmp_path):
    r = run("seed", "--intake", "samples/intake_valley_regional.yaml", "--mode", "export",
            "--estate", "samples/synthetic_estate.json", "--out", str(tmp_path / "seed.json"))
    assert r.returncode == 0, r.stdout + r.stderr
    seed = json.loads((tmp_path / "seed.json").read_text(encoding="utf-8"))
    assert seed["mode"] == "export"
    assert seed["entry"]["asset"] == "vpngw01"


def test_tenable_mode_without_keys_fails_cleanly(tmp_path):
    r = run("seed", "--intake", "samples/intake_valley_regional.yaml", "--mode", "tenable", "--out", str(tmp_path / "seed.json"))
    assert r.returncode == 2
    assert "TENABLE_ACCESS_KEY" in r.stderr


def test_validate_packs_from_cli():
    r = run("validate", "packs")
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_clock_flag_has_a_plain_question():
    from ttx.cli import flags_for_industry

    rows = flags_for_industry(None)
    assert rows, "no flags found"
    missing = [r["flag"] for r in rows if not r["question"]]
    assert not missing, f"add these to schemas/flags.yaml: {missing}"


def test_flags_are_filtered_by_industry_and_state():
    from ttx.cli import flags_for_industry

    health_ca = {r["flag"] for r in flags_for_industry("healthcare", states=["CA"])}
    assert "ca_licensed_health_facility" in health_ca
    assert "article_28_hospital" not in health_ca  # New York only
    assert "occ_supervised" not in health_ca       # a banking status
    assert "pci_merchant" in health_ca             # shared by every industry
    bank = {r["flag"] for r in flags_for_industry("banking", states=["NY"])}
    assert {"occ_supervised", "credit_union", "nydfs_licensed"} <= bank


def test_flags_command_from_cli():
    r = run("flags", "--industry", "banking", "--states", "TX")
    assert r.returncode == 0, r.stderr
    assert "credit union" in r.stdout
