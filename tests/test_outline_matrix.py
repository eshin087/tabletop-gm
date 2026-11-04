"""The deterministic outline is valid and buildable for every pack, duration, and severity."""

import pytest

from ttx.build import build_all
from ttx.clock_engine import evaluate
from ttx.outline import build_outline, stamp_approval
from ttx.packs import list_packs
from ttx.seed_engine import Estate, load_sample_estate, select_seed
from ttx.validators import validate_exercise_pack

FLAGS = {
    "banking": ["occ_supervised", "bank_federally_insured"],
    "insurance": ["nydfs_licensed", "insurer_licensed"],
    "federal_contractors": ["defense_contractor"],
    "energy_utilities": ["nerc_registered_entity"],
    "public_sector": ["state_agency"],
    "higher_education": ["title_iv_institution"],
}
DATA = {
    "healthcare": ["PHI", "PII"], "banking": ["PFI", "PII"], "insurance": ["PII", "PHI"], "retail_ecommerce": ["PCI", "PII"],
    "federal_contractors": ["CUI"], "manufacturing_ot": ["OT", "trade_secrets"], "energy_utilities": ["OT", "PII"],
    "higher_education": ["FERPA", "PII"], "public_sector": ["PII"], "saas_technology": ["PII"],
}


def _intake(industry, duration=90, severity=3, mode="sample"):
    return {
        "organization": {"name": f"Example {industry} org", "short_name": "EX"},
        "industry": industry,
        "countries": ["US"],
        "states": ["NY", "TX"],
        "data_types": DATA.get(industry, ["PII"]),
        "public_company": True,
        "regulated": FLAGS.get(industry, []),
        "affected_estimate": 5000,
        "severity_level": severity,
        "duration_minutes": duration,
        "audience": "mixed",
        "environment": {"mode": mode, "estate_file": "samples/synthetic_estate.json"},
        "exercise": {"date": "2026-11-06"},
    }


@pytest.mark.parametrize("industry", list_packs())
def test_every_pack_outlines_without_a_plan(industry):
    intake = _intake(industry)
    seed = select_seed(load_sample_estate("samples/synthetic_estate.json"), intake)
    clocks = evaluate(intake)
    pack = build_outline(intake, seed, clocks, None)
    result = validate_exercise_pack(pack)
    assert result.ok, result.summary()
    assert all(j["procedure_tested"]["type"] in {"pack_default", "plan_silent"} for j in pack["injects"])
    assert pack["clocks"], f"no clocks for {industry}"


@pytest.mark.parametrize("duration,severity", [(60, 1), (90, 2), (180, 4)])
def test_durations_and_severities_with_the_sample_plan(duration, severity, org_plan, tmp_path):
    intake = _intake("healthcare", duration, severity)
    intake["regulated"] = ["ca_licensed_health_facility"]
    intake["states"] = ["CA"]
    seed = select_seed(load_sample_estate("samples/synthetic_estate.json"), intake)
    pack = build_outline(intake, seed, evaluate(intake), org_plan)
    result = validate_exercise_pack(pack)
    assert result.ok, result.summary()
    assert len(pack["injects"]) == {60: 5, 90: 7, 180: 10}[duration]
    stamp_approval(pack, "test")
    built = build_all(pack, tmp_path)
    assert len(built) == 6


def test_no_exposure_data_builds_a_labeled_generic_scenario(tmp_path):
    intake = _intake("banking", mode="none")
    seed = select_seed(Estate(assets=[], findings=[], source="none", mode="none"), intake)
    pack = build_outline(intake, seed, evaluate(intake), None)
    result = validate_exercise_pack(pack)
    assert result.ok, result.summary()
    assert all(j["source"]["type"] == "assumption" for j in pack["injects"])
    stamp_approval(pack, "test")
    assert build_all(pack, tmp_path)


def test_clocks_outside_the_scenario_data_are_listed_not_used():
    intake = _intake("retail_ecommerce")
    intake["regulated"] = ["pci_merchant"]
    seed = select_seed(load_sample_estate("samples/synthetic_estate.json"), intake)
    pack = build_outline(intake, seed, evaluate(intake), None)
    used = {c["id"] for c in pack["clocks"]}
    for out in pack["clocks_outside_scenario"]:
        assert out["id"] not in used
        assert out["reason"]
