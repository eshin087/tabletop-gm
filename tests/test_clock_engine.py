from datetime import datetime, timezone

import pytest

from ttx.clock_engine import add_business_days, applies, evaluate, shortest_clock


def _bank_intake(**over):
    base = {
        "organization": {"name": "Sample Bank"},
        "industry": "banking",
        "countries": ["US"],
        "states": ["TX"],
        "data_types": ["PFI", "PII"],
        "public_company": False,
        "regulated": ["occ_supervised", "bank_federally_insured"],
        "affected_estimate": 12000,
    }
    base.update(over)
    return base


def test_banking_notification_incident_is_36_hours():
    result = evaluate(_bank_intake())
    by_id = {c["id"]: c for c in result["clocks"]}
    assert by_id["occ_notification_incident_36h"]["deadline_hours"] == 36
    assert by_id["occ_notification_incident_36h"]["source_url"].startswith("https://")
    assert by_id["occ_notification_incident_36h"]["tier"] in {"verified", "researched"}
    # the Fed and FDIC clocks need their own flags
    assert "frb_notification_incident_36h" not in by_id
    assert "fdic_notification_incident_36h" not in by_id


def test_credit_union_gets_72_hours_not_36():
    result = evaluate(_bank_intake(regulated=["credit_union", "bank_federally_insured"]))
    by_id = {c["id"]: c for c in result["clocks"]}
    assert by_id["ncua_reportable_cyber_incident_72h"]["deadline_hours"] == 72
    assert "occ_notification_incident_36h" not in by_id


def test_hipaa_individual_notice_is_60_days(intake):
    result = evaluate(intake)
    by_id = {c["id"]: c for c in result["clocks"]}
    assert by_id["hipaa_individual_notice"]["deadline_hours"] == 60 * 24
    assert by_id["hipaa_hhs_notice_500_or_more"]["deadline_hours"] == 60 * 24
    assert by_id["hipaa_individual_notice"]["citation"] == "45 CFR 164.404(b)"


def test_min_affected_threshold_excludes_small_breaches(intake):
    small = dict(intake, affected_estimate=120)
    result = evaluate(small)
    ids = {c["id"] for c in result["clocks"]}
    assert "hipaa_individual_notice" in ids
    assert "hipaa_hhs_notice_500_or_more" not in ids
    assert any(x["id"] == "hipaa_hhs_notice_500_or_more" for x in result["excluded"])


def test_flag_matched_clock_loads_from_another_pack():
    # a bank that is also NYDFS licensed should get the insurance pack's 500.17 clock when it exists
    result = evaluate(_bank_intake(states=["NY"], regulated=["occ_supervised", "bank_federally_insured", "nydfs_licensed"]))
    nydfs = [c for c in result["clocks"] if "nydfs" in c["id"]]
    if nydfs:  # the insurance pack is researched separately; skip if it has not landed
        assert all(c["pack"] == "insurance" for c in nydfs)
        assert any("flags" in reason for c in nydfs for reason in c["applies_because"])
    else:
        pytest.skip("insurance pack not present")


def test_researched_clocks_raise_the_banner(intake):
    result = evaluate(intake)
    assert result["banner"]["show"] is True
    assert "verify before exercise" in result["banner"]["text"].lower()
    assert set(result["researched_clock_ids"]) == {c["id"] for c in result["clocks"] if c["tier"] == "researched"}


def test_met_and_missed_by_hours(intake):
    trigger = "2026-11-06T09:00:00+00:00"
    on_time = "2026-12-20T09:00:00+00:00"   # 44 days later
    late = "2027-01-20T09:00:00+00:00"      # 75 days later
    result = evaluate(intake, {"trigger_at": trigger, "notifications": {"hipaa_individual_notice": on_time, "hipaa_hhs_notice_500_or_more": late}})
    by_id = {c["id"]: c for c in result["clocks"]}
    assert by_id["hipaa_individual_notice"]["met"] is True
    assert by_id["hipaa_individual_notice"]["margin_hours"] == 16 * 24
    assert by_id["hipaa_hhs_notice_500_or_more"]["met"] is False
    assert by_id["hipaa_media_notice"]["met"] is None  # not notified yet


def test_business_days_skip_weekends():
    friday = datetime(2026, 11, 6, 9, 0, tzinfo=timezone.utc)
    assert add_business_days(friday, 1).weekday() == 0  # Monday
    assert add_business_days(friday, 5) == datetime(2026, 11, 13, 9, 0, tzinfo=timezone.utc)


def test_applies_conditions():
    clock = {"applies_when": {"countries": ["US"], "public_company": True}}
    assert applies(clock, {"countries": ["US"], "public_company": True})[0]
    assert not applies(clock, {"countries": ["US"], "public_company": False})[0]
    assert not applies(clock, {"countries": ["DE"], "public_company": True})[0]
    assert applies({"applies_when": {}}, {})[0]


def test_unknown_pack_is_an_error():
    with pytest.raises(FileNotFoundError):
        evaluate(_bank_intake(industry="not_a_pack"))


def test_shortest_clock(intake):
    result = evaluate(intake)
    tight = shortest_clock(result)
    assert tight is not None
    assert tight["id"] == "ca_health_facility_unauthorized_access_15bd"
