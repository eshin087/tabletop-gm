import copy

import pytest

from ttx import validators as v
from ttx.packs import list_packs
from ttx.plan_ingest import documents_index, ingest


def _minimal_clock(**over):
    c = {
        "id": "test_clock", "name": "Test", "deadline_hours": 72, "deadline_text": "72 hours", "citation": "x",
        "source_url": "https://example.gov/rule", "verified_date": "2026-11-03", "tier": "verified", "applies_when": {},
    }
    c.update(over)
    return c


def test_clock_without_source_link_fails():
    r = v.Result("t")
    v.validate_clock(_minimal_clock(source_url=""), r, "test")
    assert not r.ok
    assert any("source_url" in e for e in r.errors)


def test_researched_clock_is_flagged_but_passes():
    r = v.Result("t")
    v.validate_clock(_minimal_clock(tier="researched"), r, "test")
    assert r.ok
    assert any("researched" in w for w in r.warnings)


def test_bad_tier_and_bad_date_fail():
    r = v.Result("t")
    v.validate_clock(_minimal_clock(tier="guessed", verified_date="yesterday"), r, "test")
    assert any("tier" in e for e in r.errors)
    assert any("verified_date" in e for e in r.errors)


def test_every_shipped_pack_validates():
    results = v.validate_all_packs()
    failures = [r.summary() for r in results if not r.ok]
    assert not failures, "\n".join(failures)
    assert len(list_packs()) >= 2


def test_org_plan_quote_not_in_source_fails(org_plan):
    docs = documents_index(ingest(["samples/sample_ir_plan.md"]))
    assert v.validate_org_plan(org_plan, docs).ok
    bad = copy.deepcopy(org_plan)
    bad["items"][0]["quote"] = "The Chief Marketing Officer serves as Incident Commander for all incidents."
    r = v.validate_org_plan(bad, docs)
    assert not r.ok
    assert any("P1" in e and "not found" in e for e in r.errors)


def test_org_plan_quote_tolerates_whitespace_and_curly_quotes(org_plan):
    docs = documents_index(ingest(["samples/sample_ir_plan.md"]))
    plan = copy.deepcopy(org_plan)
    plan["items"][0]["quote"] = "The  Chief Information Security Officer (CISO)\nserves as Incident Commander"
    assert v.validate_org_plan(plan, docs).ok
    plan["items"][44]["quote"] = "the business associate agreement’s notification clause was met"
    assert v.validate_org_plan(plan, docs).ok


def test_org_plan_without_documents_only_warns(org_plan):
    r = v.validate_org_plan(org_plan, None)
    assert r.ok and r.warnings


def test_inject_citing_unknown_finding_fails(sample_pack):
    pack = copy.deepcopy(sample_pack)
    pack["injects"][0]["source"] = {"type": "finding", "ref": "F9999", "note": "made up"}
    r = v.validate_exercise_pack(pack)
    assert not r.ok
    assert any("F9999" in e for e in r.errors)


def test_inject_citing_unknown_assumption_fails(sample_pack):
    pack = copy.deepcopy(sample_pack)
    pack["injects"][0]["source"] = {"type": "assumption", "ref": "A77", "note": ""}
    r = v.validate_exercise_pack(pack)
    assert not r.ok


def test_inject_without_plan_quote_fails(sample_pack):
    pack = copy.deepcopy(sample_pack)
    inj = next(j for j in pack["injects"] if j["procedure_tested"]["type"] == "org_plan")
    inj["procedure_tested"]["quote"] = None
    assert not v.validate_exercise_pack(pack).ok
    inj["procedure_tested"]["quote"] = "a sentence the plan never says"
    assert not v.validate_exercise_pack(pack).ok


def test_escalation_rules_enforced(sample_pack):
    pack = copy.deepcopy(sample_pack)
    for j in pack["injects"]:
        j["flags"]["conflicting_information"] = False
    r = v.validate_exercise_pack(pack)
    assert any("conflicting information" in e for e in r.errors)


def test_inject_count_matches_duration(sample_pack):
    pack = copy.deepcopy(sample_pack)
    pack["duration_minutes"] = 60
    r = v.validate_exercise_pack(pack)
    assert any("expected 5" in e for e in r.errors)


def test_sample_pack_is_valid_and_approved(sample_pack):
    r = v.validate_exercise_pack(sample_pack, require_approval=True)
    assert r.ok, r.summary()
    assert v.check_approval(sample_pack).ok


def test_editing_after_approval_breaks_the_gate(sample_pack):
    pack = copy.deepcopy(sample_pack)
    pack["injects"][0]["title"] = "changed after sign-off"
    assert not v.check_approval(pack).ok
    assert not v.validate_exercise_pack(pack).ok


def test_unapproved_pack_fails_require_approval(sample_pack):
    pack = copy.deepcopy(sample_pack)
    pack["approval"] = {"approved": False, "approved_by": None, "approved_at": None, "outline_hash": None}
    assert v.validate_exercise_pack(pack).ok
    assert not v.validate_exercise_pack(pack, require_approval=True).ok


def test_banner_required_when_researched_clocks_present(sample_pack):
    pack = copy.deepcopy(sample_pack)
    if not pack["banner"]["researched_clock_ids"]:
        pytest.skip("sample has no researched clocks")
    pack["banner"]["show"] = False
    assert not v.validate_exercise_pack(pack).ok


def test_narrative_overlay_cannot_touch_facts(sample_pack):
    from ttx.outline import apply_narrative

    pack = copy.deepcopy(sample_pack)
    for bad in ({"injects": {"I1": {"source": {"type": "finding", "ref": "F9999"}}}},
                {"injects": {"I1": {"expected_actions": []}}},
                {"clocks": []},
                {"injects": {"I99": {"title": "x"}}}):
        with pytest.raises(ValueError):
            apply_narrative(copy.deepcopy(pack), bad)
    apply_narrative(pack, {"injects": {"I1": {"title": "A new title"}}})
    assert pack["injects"][0]["title"] == "A new title"
    assert pack["approval"]["approved"] is False
    assert v.validate_exercise_pack(pack).ok
