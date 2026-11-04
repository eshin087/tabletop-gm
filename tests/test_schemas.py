"""The documented schemas and the shipped samples agree (required keys only; validators enforce the rest)."""

import json
from pathlib import Path

from ttx.common import read_json, read_yaml
from ttx.score_engine import CLOCK_COLUMNS, DECISION_COLUMNS

SCHEMAS = Path("schemas")


def _required(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_sample_pack_has_every_required_key(sample_pack):
    schema = _required("exercise_pack.schema.json")
    assert set(schema["required"]) <= set(sample_pack)
    inj_req = set(schema["properties"]["injects"]["items"]["required"])
    for inj in sample_pack["injects"]:
        assert inj_req <= set(inj), inj_req - set(inj)
    clock_req = set(schema["properties"]["clocks"]["items"]["required"])
    for c in sample_pack["clocks"]:
        assert clock_req <= set(c)


def test_sample_seed_and_org_plan_match_schemas(sample_pack, org_plan):
    seed_schema = _required("seed.schema.json")
    assert set(seed_schema["required"]) <= set(sample_pack["seed"])
    plan_schema = _required("org_plan.schema.json")
    assert set(plan_schema["required"]) <= set(org_plan)
    item_req = set(plan_schema["properties"]["items"]["items"]["required"])
    for item in org_plan["items"]:
        assert item_req <= set(item)
        assert item["category"] in plan_schema["properties"]["items"]["items"]["properties"]["category"]["enum"]


def test_tracker_columns_doc_matches_score_engine():
    doc = read_yaml(SCHEMAS / "tracker_columns.yaml")
    assert doc["decisions"] == DECISION_COLUMNS
    assert doc["clocks"] == CLOCK_COLUMNS


def test_host_tracker_doc_matches_the_builder():
    from ttx.build import tracker

    doc = read_yaml(SCHEMAS / "host_tracker.yaml")
    assert doc["speed"] == tracker.SPEED
    assert [str(x) for x in doc["discussion"]] == tracker.DISCUSSION
    assert doc["plan_step"] == tracker.PLAN_STEP
    assert doc["documented"] == tracker.DOCUMENTED
    assert doc["clock_timing"] == tracker.CLOCK_TIMING
