import copy
import csv
import json

import pytest

from ttx.seed_engine import (
    Estate, internet_facing, load_export, load_sample_estate, map_headers, normalize_asset, normalize_finding,
    select_seed,
)
from ttx.validators import validate_seed


def test_entry_prefers_kev_internet_facing_over_higher_cvss_internal(estate, intake):
    seed = select_seed(estate, intake)
    # ehr-app01 carries Log4Shell (CVSS 10.0, KEV, VPR 9.9) but is internal.
    assert seed["entry"]["asset"] == "vpngw01"
    assert seed["entry"]["cve"] == "CVE-2025-0282"
    assert seed["entry"]["kev"] is True
    assert seed["entry"]["rule"] == "kev_internet_facing"
    assert seed["entry"]["internet_facing_rule"] == "intake_tag"
    internal = [c for c in seed["candidates"]["entry"] if c["asset"] == "ehr-app01"]
    assert internal == []


def test_sample_seed_shape_and_rules(estate, intake):
    seed = select_seed(estate, intake)
    assert seed["pivot"]["asset"] == "dc1"
    assert seed["pivot"]["rule"] == "identity_tier_hostname"
    assert seed["pivot"]["finding_id"] == "F2210"
    assert seed["target"]["asset"] == "sql2016"
    assert seed["target"]["rule"] == "tag_match"
    assert "PHI" in seed["target"]["data"]
    assert seed["path_source"] == "inferred"
    assert len(seed["findings_cited"]) <= 3
    assert validate_seed(seed).ok


def test_fixed_findings_are_ignored(estate, intake):
    seed = select_seed(estate, intake)
    assert "F2901" not in seed["findings_cited"]
    assert all(c["finding_id"] != "F2901" for c in seed["candidates"]["entry"])


def test_internet_facing_rule_order():
    tagged = normalize_asset({"id": "1", "hostnames": ["a"], "ipv4s": ["10.0.0.1"], "tags": [{"key": "Exposure", "value": "Internet"}]})
    public = normalize_asset({"id": "2", "hostnames": ["b"], "ipv4s": ["198.51.100.7"]})
    field = normalize_asset({"id": "3", "hostnames": ["c"], "ipv4s": ["10.0.0.3"], "internet_exposed": True})
    private = normalize_asset({"id": "4", "hostnames": ["d"], "ipv4s": ["192.168.1.9", "100.64.0.1"]})
    assert internet_facing(tagged, ["Exposure: Internet"]) == (True, "intake_tag")
    assert internet_facing(public, ["Exposure: Internet"]) == (True, "public_ipv4")
    assert internet_facing(field, ["Exposure: Internet"]) == (True, "tenable_exposure_field")
    assert internet_facing(private, ["Exposure: Internet"]) == (False, None)


def test_vpr_breaks_ties_among_kev_findings(estate, intake):
    e = copy.deepcopy(estate)
    for f in e.findings:
        if f["finding_id"] == "F1101":  # win2019 ProxyShell, KEV
            f["vpr"] = 9.9
    seed = select_seed(e, intake)
    assert seed["entry"]["asset"] == "win2019"
    assert seed["entry"]["finding_id"] == "F1101"


def test_generic_mode_labels_every_assumption(intake):
    empty = Estate(assets=[], findings=[], source="none", mode="none")
    seed = select_seed(empty, intake)
    assert seed["entry"]["rule"] == "assumption"
    assert seed["pivot"]["rule"] == "assumption"
    assert seed["target"]["rule"] == "assumption"
    ids = {a["id"] for a in seed["assumptions"]}
    assert seed["entry"]["assumption"] in ids
    assert seed["pivot"]["assumption"] in ids
    assert seed["target"]["assumption"] in ids
    assert seed["findings_cited"] == []
    assert validate_seed(seed).ok


def test_pivot_without_finding_records_assumption(estate, intake):
    e = copy.deepcopy(estate)
    e.findings = [f for f in e.findings if f["asset_id"] not in {"a-0010", "a-0011"}]
    seed = select_seed(e, intake)
    assert seed["pivot"]["asset"] in {"dc1", "dc2"}
    assert seed["pivot"]["finding_id"] is None
    assert seed["pivot"]["technique"].startswith("credential reuse")
    assert seed["pivot"]["assumption"] in {a["id"] for a in seed["assumptions"]}


def test_attack_path_data_overrides_inference(estate, intake):
    e = copy.deepcopy(estate)
    e.attack_paths = [{"entry": "vpngw01", "pivot": "hvhost01", "technique": "hypervisor management access"}]
    seed = select_seed(e, intake)
    assert seed["path_source"] == "tenable_apa"
    assert seed["pivot"]["asset"] == "hvhost01"
    assert seed["pivot"]["rule"] == "tenable_attack_path"


def test_csv_export_with_tenable_headers_loads(tmp_path, intake):
    headers = ["Plugin ID", "CVE", "CVSS v3.0 Base Score", "Risk", "Host", "Protocol", "Port", "Name",
               "Asset UUID", "Vulnerability State", "IP Address", "OS", "VPR Score", "EPSS Score",
               "CISA Known Exploited", "Exploit Available", "First Found", "Last Found"]
    rows = [
        ["214055", "CVE-2025-0282", "9.0", "Critical", "vpngw01", "tcp", "443", "Ivanti Connect Secure overflow",
         "u-1", "Open", "203.0.113.10", "Ivanti", "9.6", "0.92", "true", "true", "2026-09-01", "2026-11-01"],
        ["155999", "CVE-2021-44228", "10.0", "Critical", "ehr-app01", "tcp", "8080", "Log4Shell",
         "u-2", "Open", "10.20.2.20", "RHEL", "9.9", "0.98", "true", "true", "2026-09-01", "2026-11-01"],
        ["181040", "CVE-2023-36728", "5.5", "High", "sql2016", "tcp", "1433", "SQL Server update",
         "u-3", "Open", "10.20.2.15", "Windows Server 2016", "6.7", "0.02", "false", "false", "2026-09-01", "2026-11-01"],
        ["141462", "CVE-2020-1472", "10.0", "Critical", "dc1", "tcp", "445", "Zerologon",
         "u-4", "Open", "10.20.1.5", "Windows Server 2019", "9.0", "0.96", "true", "true", "2026-09-01", "2026-11-01"],
    ]
    path = tmp_path / "findings.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        w.writerows(rows)
    estate = load_export(path)
    assert estate.mode == "export"
    assert len(estate.findings) == 4
    f = next(x for x in estate.findings if x["hostname"] == "vpngw01")
    assert f["kev"] is True and f["vpr"] == 9.6 and f["cve"] == ["CVE-2025-0282"]
    seed = select_seed(estate, intake)
    assert seed["entry"]["asset"] == "vpngw01"
    assert seed["entry"]["internet_facing_rule"] == "public_ipv4"
    assert seed["pivot"]["asset"] == "dc1"
    assert seed["target"]["asset"] == "sql2016"
    assert seed["target"]["rule"] == "hostname_heuristic"


def test_json_export_with_nested_tenable_shape_loads(tmp_path):
    record = {
        "finding_id": "X1",
        "asset": {"uuid": "u-9", "hostname": "win2019", "ipv4": "203.0.113.22", "device_type": "general-purpose", "operating_system": "Windows Server 2019"},
        "plugin": {"id": 152854, "name": "ProxyShell", "cve": ["CVE-2021-34473"], "vpr": {"score": 9.2, "on_cisa_kev": True},
                   "epss_score": 0.97, "exploit_available": True, "cvss3_base_score": 9.8},
        "severity": "critical", "state": "OPEN", "first_found": "2026-09-01", "port": {"port": 443, "protocol": "TCP"}, "source": "NESSUS_SCAN",
    }
    path = tmp_path / "findings.json"
    path.write_text(json.dumps([record]), encoding="utf-8")
    estate = load_export(path)
    assert estate.findings[0]["kev"] is True
    assert estate.findings[0]["asset_id"] == "u-9"
    assert estate.assets[0]["hostname"] == "win2019"


def test_header_mapping_is_fuzzy():
    aliases = {"vpr": ["vpr score", "vpr"], "plugin_name": ["plugin name", "name"], "hostname": ["host", "hostname"]}
    mapping = map_headers(["VPR_Score", "Plugin-Name", "Host Name"], aliases)
    assert mapping == {"vpr": "VPR_Score", "plugin_name": "Plugin-Name", "hostname": "Host Name"}


def test_normalize_finding_reads_nested_kev_flag():
    f = normalize_finding({"finding_id": "F", "asset": {"uuid": "a"}, "plugin": {"id": 1, "name": "n", "vpr": {"score": "8.1", "on_cisa_kev": "true"}}, "severity": "High", "state": "open"})
    assert f["kev"] is True and f["vpr"] == 8.1 and f["severity"] == "high"


def test_validator_rejects_more_than_three_findings(estate, intake):
    seed = select_seed(estate, intake)
    seed["findings_cited"] = ["F1", "F2", "F3", "F4"]
    assert not validate_seed(seed).ok
