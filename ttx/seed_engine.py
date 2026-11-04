"""Scenario seed engine.

Reads exposure data from one of three modes (Tenable API, an uploaded export,
or the synthetic sample estate) and picks the attack path deterministically:

  entry   = exploitable finding on an internet-facing asset, prefer KEV-listed
            then highest VPR
  pivot   = identity-tier or high-ACR server reachable from the entry
  target  = highest-criticality asset holding the intake's data types

Every choice records the rule that fired. At most three findings are cited.
When there is no data, the seed is generic and every assumption is labeled.
Read-only everywhere.
"""

from __future__ import annotations

import csv
import ipaddress
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from . import __version__
from .common import as_list, now_iso, read_json, read_yaml, schemas_dir, today_iso, write_json

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0, "informational": 0}
OPEN_STATES = {"open", "reopened", "active", "new", "resurfaced", ""}

IDENTITY_HOST_PATTERNS = [
    r"^dc\d*\b", r"\bdc\d*$", r"^ad\d*\b", r"^adfs", r"ldap", r"\bidp\b", r"domain", r"^kdc",
    r"okta", r"entra", r"azuread", r"radius", r"^pdc", r"^bdc",
]
IDENTITY_SOFTWARE_PATTERNS = [r"active_directory", r"ad_domain_services", r"adfs", r"ldap", r"kerberos"]
IDENTITY_TAG_VALUES = {"domain controller", "identity", "directory", "idp"}

# Data type -> hostname / software / tag heuristics for the crown jewel
DATA_TYPE_HINTS: dict[str, dict[str, list[str]]] = {
    "PHI": {
        "host": ["ehr", "emr", "epic", "cerner", "meditech", "pacs", "his", "lis", "clinical", "patient", "sql", "db", "target"],
        "software": ["sql_server", "oracle:database", "postgresql", "mysql", "mongodb", "epic", "cerner", "meditech", "dicom"],
        "tag": ["phi", "ehr", "clinical", "patient"],
    },
    "PII": {
        "host": ["hr", "crm", "erp", "sql", "db", "sap", "workday", "target", "file"],
        "software": ["sql_server", "oracle:database", "postgresql", "mysql", "mongodb", "sap"],
        "tag": ["pii", "hr", "customer"],
    },
    "PFI": {
        "host": ["core", "swift", "fedline", "wire", "ach", "loan", "sql", "db", "target"],
        "software": ["sql_server", "oracle:database", "db2", "postgresql"],
        "tag": ["pfi", "core", "payments", "financial"],
    },
    "PCI": {
        "host": ["pos", "payment", "card", "pan", "cde", "sql", "db"],
        "software": ["sql_server", "oracle:database", "postgresql", "mysql"],
        "tag": ["pci", "cde", "cardholder", "payments"],
    },
    "FERPA": {
        "host": ["sis", "student", "banner", "registrar", "lms", "sql", "db"],
        "software": ["sql_server", "oracle:database", "postgresql", "mysql"],
        "tag": ["ferpa", "student", "sis"],
    },
    "CUI": {
        "host": ["cui", "plm", "cad", "engineering", "file", "share", "sql", "db"],
        "software": ["sql_server", "oracle:database", "sharepoint", "postgresql"],
        "tag": ["cui", "itar", "controlled"],
    },
    "OT": {
        "host": ["scada", "historian", "hmi", "plc", "mes", "ot", "ics"],
        "software": ["historian", "wonderware", "citect", "ignition"],
        "tag": ["ot", "scada", "ics", "plant"],
    },
    "trade_secrets": {
        "host": ["plm", "cad", "git", "source", "repo", "file", "share", "research"],
        "software": ["gitlab", "bitbucket", "sharepoint"],
        "tag": ["ip", "research", "source"],
    },
}
GENERIC_DB_SOFTWARE = ["sql_server", "oracle:database", "postgresql", "mysql", "mongodb", "db2"]


@dataclass
class Estate:
    assets: list[dict]
    findings: list[dict]
    source: str
    mode: str
    attack_paths: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Normalization
# --------------------------------------------------------------------------- #

def _norm_header(text: str) -> str:
    text = str(text or "").strip().lower()
    text = re.sub(r"[\._\-/\\\(\)\[\]:]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_column_map() -> dict:
    path = schemas_dir() / "export_columns.yaml"
    return read_yaml(path)


def map_headers(headers: Iterable[str], aliases: dict[str, list[str]]) -> dict[str, str]:
    """Return {canonical_field: actual_header} using exact then fuzzy matching."""
    normalized = {h: _norm_header(h) for h in headers}
    mapping: dict[str, str] = {}
    used: set[str] = set()
    # pass 1: exact normalized matches, in field order
    for field_name, alias_list in aliases.items():
        norm_aliases = [_norm_header(a) for a in alias_list]
        for header, norm in normalized.items():
            if header in used:
                continue
            if norm in norm_aliases:
                mapping[field_name] = header
                used.add(header)
                break
    # pass 2: containment for the rest
    for field_name, alias_list in aliases.items():
        if field_name in mapping:
            continue
        norm_aliases = [_norm_header(a) for a in alias_list if len(_norm_header(a)) >= 3]
        for header, norm in normalized.items():
            if header in used:
                continue
            if any(a == norm or (len(norm) >= 3 and (a in norm or norm in a)) for a in norm_aliases):
                mapping[field_name] = header
                used.add(header)
                break
    return mapping


def _get(d: dict, *path: str, default=None):
    cur: Any = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "yes", "y", "1", "t"}:
        return True
    if text in {"false", "no", "n", "0", "f"}:
        return False
    return None


def _split_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v not in (None, "")]
    text = str(value).strip()
    if not text:
        return []
    return [p.strip() for p in re.split(r"[,;|\n]+", text) if p.strip()]


_NON_PUBLIC_V4 = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12",
    "192.0.0.0/24", "192.168.0.0/16", "198.18.0.0/15", "224.0.0.0/4", "240.0.0.0/4", "255.255.255.255/32",
)]


def _is_public_ipv4(ip: str) -> bool:
    """RFC 1918, loopback, link-local, CGNAT, benchmarking, and multicast are not public.

    The documentation ranges (192.0.2/24, 198.51.100/24, 203.0.113/24) count as public so
    synthetic estates can show internet-facing hosts without using anyone's real address.
    """
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return False
    if addr.version != 4:
        return False
    return not any(addr in net for net in _NON_PUBLIC_V4)


def normalize_asset(raw: dict) -> dict:
    hostnames = _split_list(raw.get("hostnames")) or _split_list(raw.get("hostname"))
    fqdns = _split_list(raw.get("fqdns")) or _split_list(raw.get("fqdn"))
    ipv4s = _split_list(raw.get("ipv4s")) or _split_list(raw.get("ipv4"))
    acr = _to_float(_get(raw, "ratings", "acr", "score"))
    if acr is None:
        acr = _to_float(raw.get("acr_score"))
    if acr is None:
        acr = _to_float(raw.get("acr"))
    tags = []
    for t in raw.get("tags") or []:
        if isinstance(t, dict):
            tags.append({"key": str(t.get("key", "")), "value": str(t.get("value", ""))})
        elif isinstance(t, str) and ":" in t:
            k, v = t.split(":", 1)
            tags.append({"key": k.strip(), "value": v.strip()})
    internet_exposed = _to_bool(raw.get("internet_exposed"))
    if internet_exposed is None:
        exposure = raw.get("exposure") or raw.get("network_exposure")
        if isinstance(exposure, str):
            internet_exposed = exposure.strip().lower() in {"internet", "external", "public", "internet-facing"}
    aws = any(k.startswith("aws_") and raw.get(k) for k in raw)
    azure = any(k.startswith("azure_") and raw.get(k) for k in raw)
    sources = []
    for s in raw.get("sources") or []:
        if isinstance(s, dict):
            sources.append(str(s.get("name", "")))
        else:
            sources.append(str(s))
    hostname = hostnames[0] if hostnames else (fqdns[0] if fqdns else (ipv4s[0] if ipv4s else str(raw.get("id", "unknown"))))
    return {
        "id": str(raw.get("id") or raw.get("uuid") or raw.get("asset_uuid") or hostname),
        "hostname": hostname,
        "hostnames": hostnames,
        "fqdns": fqdns,
        "ipv4s": ipv4s,
        "acr": acr,
        "exposure_score": _to_float(raw.get("exposure_score")),
        "tags": tags,
        "system_types": _split_list(raw.get("system_types")),
        "operating_systems": _split_list(raw.get("operating_systems")) or _split_list(raw.get("operating_system")),
        "installed_software": _split_list(raw.get("installed_software")),
        "device_type": str(raw.get("device_type") or ""),
        "sources": sources,
        "internet_exposed": internet_exposed,
        "cloud": "aws" if aws else ("azure" if azure else None),
    }


def normalize_finding(raw: dict) -> dict:
    asset = raw.get("asset") if isinstance(raw.get("asset"), dict) else {}
    plugin = raw.get("plugin") if isinstance(raw.get("plugin"), dict) else {}
    port = raw.get("port") if isinstance(raw.get("port"), dict) else {}
    vpr = _to_float(_get(plugin, "vpr", "score"))
    if vpr is None:
        vpr = _to_float(raw.get("vpr"))
    kev = _to_bool(_get(plugin, "vpr", "on_cisa_kev"))
    if kev is None:
        kev = _to_bool(raw.get("kev"))
    severity = str(raw.get("severity") or "").strip().lower()
    cves = _split_list(plugin.get("cve")) or _split_list(raw.get("cve"))
    return {
        "finding_id": str(raw.get("finding_id") or raw.get("id") or ""),
        "asset_id": str(asset.get("uuid") or raw.get("asset_id") or raw.get("asset_uuid") or ""),
        "hostname": str(asset.get("hostname") or raw.get("hostname") or ""),
        "ipv4": str(asset.get("ipv4") or raw.get("ipv4") or ""),
        "device_type": str(asset.get("device_type") or raw.get("device_type") or ""),
        "os": str(asset.get("operating_system") or raw.get("os") or ""),
        "plugin_id": str(plugin.get("id") or raw.get("plugin_id") or ""),
        "plugin_name": str(plugin.get("name") or raw.get("plugin_name") or ""),
        "cve": cves,
        "vpr": vpr,
        "epss": _to_float(plugin.get("epss_score") if plugin else raw.get("epss")),
        "kev": bool(kev) if kev is not None else False,
        "exploit_available": bool(_to_bool(plugin.get("exploit_available") if plugin else raw.get("exploit_available")) or False),
        "severity": severity,
        "cvss3": _to_float(plugin.get("cvss3_base_score") if plugin else raw.get("cvss3")),
        "state": str(raw.get("state") or "").strip().lower(),
        "first_found": str(raw.get("first_found") or ""),
        "last_found": str(raw.get("last_found") or ""),
        "port": port.get("port") if port else raw.get("port"),
        "protocol": port.get("protocol") if port else raw.get("protocol"),
        "source": str(raw.get("source") or ""),
    }


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #

def load_sample_estate(path: str | os.PathLike) -> Estate:
    data = read_json(path)
    assets = [normalize_asset(a) for a in data.get("assets", [])]
    findings = [normalize_finding(f) for f in data.get("findings", [])]
    return Estate(
        assets=assets,
        findings=findings,
        source=f"sample_estate:{Path(path).name}",
        mode="sample",
        attack_paths=list(data.get("attack_paths") or []),
        notes=[f"synthetic estate '{data.get('name', Path(path).name)}'"],
    )


def _rows_to_findings(rows: list[dict], headers: list[str]) -> list[dict]:
    colmap = load_column_map()
    mapping = map_headers(headers, colmap["findings"])
    out = []
    for i, row in enumerate(rows, start=1):
        rec = {field: row.get(header) for field, header in mapping.items()}
        raw = {
            "finding_id": rec.get("finding_id") or f"ROW{i}",
            "asset_id": rec.get("asset_id") or rec.get("hostname") or rec.get("ipv4") or f"asset-{i}",
            "hostname": rec.get("hostname") or rec.get("fqdn") or rec.get("ipv4") or "",
            "ipv4": rec.get("ipv4") or "",
            "device_type": rec.get("device_type") or "",
            "os": rec.get("os") or "",
            "plugin_id": rec.get("plugin_id") or "",
            "plugin_name": rec.get("plugin_name") or "",
            "cve": rec.get("cve") or "",
            "vpr": rec.get("vpr"),
            "epss": rec.get("epss"),
            "kev": rec.get("kev"),
            "exploit_available": rec.get("exploit_available"),
            "severity": rec.get("severity") or "",
            "cvss3": rec.get("cvss3"),
            "state": rec.get("state") or "",
            "first_found": rec.get("first_found") or "",
            "last_found": rec.get("last_found") or "",
            "port": rec.get("port"),
            "protocol": rec.get("protocol"),
            "source": rec.get("source") or "export",
        }
        out.append(normalize_finding(raw))
    return out


def _rows_to_assets(rows: list[dict], headers: list[str]) -> list[dict]:
    colmap = load_column_map()
    mapping = map_headers(headers, colmap["assets"])
    out = []
    for i, row in enumerate(rows, start=1):
        rec = {field: row.get(header) for field, header in mapping.items()}
        tags = []
        for t in _split_list(rec.get("tags")):
            if ":" in t:
                k, v = t.split(":", 1)
                tags.append({"key": k.strip(), "value": v.strip()})
        raw = {
            "id": rec.get("id") or rec.get("hostnames") or f"asset-{i}",
            "hostnames": rec.get("hostnames") or "",
            "fqdns": rec.get("fqdns") or "",
            "ipv4s": rec.get("ipv4s") or "",
            "acr_score": rec.get("acr"),
            "exposure_score": rec.get("exposure_score"),
            "tags": tags,
            "system_types": rec.get("system_types") or "",
            "operating_systems": rec.get("operating_systems") or "",
            "installed_software": rec.get("installed_software") or "",
            "device_type": rec.get("device_type") or "",
            "internet_exposed": rec.get("internet_exposed"),
            "aws_ec2_instance_id": rec.get("aws_instance_id"),
            "azure_resource_id": rec.get("azure_resource_id"),
        }
        out.append(normalize_asset(raw))
    return out


def _read_csv(path: Path) -> tuple[list[dict], list[str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        headers = list(reader.fieldnames or [])
    return rows, headers


def _read_json_export(path: Path) -> tuple[list[dict], list[dict]]:
    data = read_json(path)
    findings_raw: list[dict] = []
    assets_raw: list[dict] = []
    if isinstance(data, list):
        for rec in data:
            if isinstance(rec, dict) and ("plugin" in rec or "finding_id" in rec or "severity" in rec):
                findings_raw.append(rec)
            elif isinstance(rec, dict):
                assets_raw.append(rec)
    elif isinstance(data, dict):
        findings_raw = list(data.get("findings") or data.get("vulnerabilities") or [])
        assets_raw = list(data.get("assets") or [])
    return findings_raw, assets_raw


def _assets_from_findings(findings: list[dict]) -> list[dict]:
    """Build a minimal asset table from findings when no asset export is given."""
    by_id: dict[str, dict] = {}
    for f in findings:
        aid = f["asset_id"] or f["hostname"] or f["ipv4"]
        if not aid:
            continue
        a = by_id.setdefault(aid, {
            "id": aid, "hostnames": [], "ipv4s": [], "operating_systems": [], "device_type": f["device_type"],
        })
        if f["hostname"] and f["hostname"] not in a["hostnames"]:
            a["hostnames"].append(f["hostname"])
        if f["ipv4"] and f["ipv4"] not in a["ipv4s"]:
            a["ipv4s"].append(f["ipv4"])
        if f["os"] and f["os"] not in a["operating_systems"]:
            a["operating_systems"].append(f["os"])
    return [normalize_asset(a) for a in by_id.values()]


def load_export(findings_path: str | os.PathLike, assets_path: str | os.PathLike | None = None) -> Estate:
    fpath = Path(findings_path)
    notes = []
    assets: list[dict] = []
    if fpath.suffix.lower() == ".csv":
        rows, headers = _read_csv(fpath)
        findings = _rows_to_findings(rows, headers)
        notes.append(f"findings CSV '{fpath.name}' with {len(rows)} rows; headers mapped by export_columns.yaml")
    elif fpath.suffix.lower() == ".json":
        findings_raw, assets_raw = _read_json_export(fpath)
        findings = [normalize_finding(f) for f in findings_raw]
        assets = [normalize_asset(a) for a in assets_raw]
        notes.append(f"findings JSON '{fpath.name}' with {len(findings)} records")
    elif fpath.suffix.lower() == ".nessus":
        findings, assets = _load_nessus(fpath)
        notes.append(f".nessus '{fpath.name}' with {len(findings)} findings")
    else:
        raise ValueError(f"unsupported export format: {fpath.suffix} (use .csv, .json, or .nessus)")
    if assets_path:
        apath = Path(assets_path)
        if apath.suffix.lower() == ".csv":
            rows, headers = _read_csv(apath)
            assets = _rows_to_assets(rows, headers)
        else:
            data = read_json(apath)
            raw_assets = data.get("assets") if isinstance(data, dict) else data
            assets = [normalize_asset(a) for a in raw_assets or []]
        notes.append(f"assets export '{apath.name}' with {len(assets)} records")
    if not assets:
        assets = _assets_from_findings(findings)
        notes.append("no asset export: assets inferred from findings (no ACR; criticality defaults to hostname heuristics)")
    source = f"export:{fpath.name}" + (f"+{Path(assets_path).name}" if assets_path else "")
    return Estate(assets=assets, findings=findings, source=source, mode="export", notes=notes)


def _load_nessus(path: Path) -> tuple[list[dict], list[dict]]:
    """Minimal .nessus (XML) reader: one finding per ReportItem of severity >= 3."""
    import xml.etree.ElementTree as ET

    tree = ET.parse(path)
    findings: list[dict] = []
    assets_raw: list[dict] = []
    n = 0
    for host in tree.getroot().iter("ReportHost"):
        name = host.get("name", "")
        props = {t.get("name"): (t.text or "") for t in host.iter("tag")}
        hostname = props.get("host-fqdn") or props.get("netbios-name") or name
        assets_raw.append({
            "id": props.get("host-uuid") or hostname,
            "hostnames": [hostname],
            "ipv4s": [props.get("host-ip") or name],
            "operating_systems": [props.get("operating-system", "")],
        })
        for item in host.iter("ReportItem"):
            sev = int(item.get("severity", "0"))
            if sev < 3:
                continue
            n += 1
            cves = [c.text for c in item.findall("cve") if c.text]
            vpr = item.findtext("vpr_score")
            findings.append(normalize_finding({
                "finding_id": f"N{n}",
                "asset_id": props.get("host-uuid") or hostname,
                "hostname": hostname,
                "ipv4": props.get("host-ip") or name,
                "os": props.get("operating-system", ""),
                "plugin_id": item.get("pluginID", ""),
                "plugin_name": item.get("pluginName", ""),
                "cve": cves,
                "vpr": vpr,
                "kev": (item.findtext("cisa-known-exploited") or "").lower() == "true",
                "exploit_available": (item.findtext("exploit_available") or "").lower() == "true",
                "severity": {4: "critical", 3: "high"}.get(sev, "medium"),
                "cvss3": item.findtext("cvss3_base_score"),
                "state": "open",
                "port": item.get("port"),
                "protocol": item.get("protocol"),
                "source": "nessus",
            }))
    return findings, [normalize_asset(a) for a in assets_raw]


def load_tenable(access_key: str, secret_key: str, severities: tuple[str, ...] = ("critical", "high")) -> Estate:
    """Read-only pull from Tenable Vulnerability Management / Tenable One.

    Uses pytenable when installed, otherwise the export endpoints through urllib.
    Both paths only create temporary export jobs and read their chunks; nothing
    in the tenant is modified. Not exercised in automated tests (no network).
    """
    findings_raw: list[dict] = []
    assets_raw: list[dict] = []
    try:
        from tenable.io import TenableIO  # type: ignore

        tio = TenableIO(access_key, secret_key, vendor="Tabletop GM", product="ttx", build=__version__)
        findings_raw = list(tio.exports.vulns(severity=list(severities), state=["open", "reopened"]))
        assets_raw = list(tio.exports.assets())
        source = f"tenable_api_{today_iso()} (pytenable)"
    except ImportError:
        findings_raw, assets_raw = _tenable_export_urllib(access_key, secret_key, severities)
        source = f"tenable_api_{today_iso()} (urllib)"
    assets = [normalize_asset(a) for a in assets_raw]
    findings = [normalize_finding(f) for f in findings_raw]
    return Estate(assets=assets, findings=findings, source=source, mode="tenable",
                  notes=[f"{len(findings)} findings and {len(assets)} assets exported read-only"])


def _tenable_export_urllib(access_key: str, secret_key: str, severities: tuple[str, ...]) -> tuple[list[dict], list[dict]]:
    import urllib.request

    base = "https://cloud.tenable.com"
    headers = {
        "X-ApiKeys": f"accessKey={access_key}; secretKey={secret_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": f"Tabletop-GM/{__version__}",
    }

    def call(method: str, path: str, body: dict | None = None) -> Any:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=120) as resp:  # nosec: fixed host, read-only export
            return json.loads(resp.read().decode("utf-8"))

    def run_export(kind: str, body: dict) -> list[dict]:
        job = call("POST", f"/{kind}/export", body)
        uuid = job["export_uuid"]
        chunks: list[int] = []
        for _ in range(120):
            status = call("GET", f"/{kind}/export/{uuid}/status")
            if status.get("status") == "FINISHED":
                chunks = list(status.get("chunks_available") or [])
                break
            if status.get("status") in {"CANCELLED", "ERROR"}:
                raise RuntimeError(f"Tenable export {kind} ended with {status.get('status')}")
            time.sleep(5)
        records: list[dict] = []
        for chunk in chunks:
            records.extend(call("GET", f"/{kind}/export/{uuid}/chunks/{chunk}"))
        return records

    findings = run_export("vulns", {
        "num_assets": 500,
        "filters": {"severity": list(severities), "state": ["open", "reopened"]},
    })
    assets = run_export("assets", {"chunk_size": 1000})
    return findings, assets


def load_estate(intake: dict, mode: str | None = None, estate_file: str | None = None,
                assets_file: str | None = None, access_key: str | None = None,
                secret_key: str | None = None) -> Estate:
    env = intake.get("environment") or {}
    mode = (mode or env.get("mode") or "none").lower()
    if mode == "sample":
        path = estate_file or env.get("estate_file")
        if not path:
            raise ValueError("sample mode needs an estate file (environment.estate_file or --estate)")
        return load_sample_estate(path)
    if mode == "export":
        path = estate_file or env.get("estate_file") or env.get("findings_export")
        if not path:
            raise ValueError("export mode needs a findings export (environment.estate_file or --estate)")
        return load_export(path, assets_file or env.get("assets_export"))
    if mode == "tenable":
        access_key = access_key or os.environ.get("TENABLE_ACCESS_KEY")
        secret_key = secret_key or os.environ.get("TENABLE_SECRET_KEY")
        if not access_key or not secret_key:
            raise ValueError("tenable mode needs TENABLE_ACCESS_KEY and TENABLE_SECRET_KEY in .env or the environment")
        return load_tenable(access_key, secret_key)
    if mode == "none":
        return Estate(assets=[], findings=[], source="none", mode="none", notes=["no exposure data; generic scenario"])
    raise ValueError(f"unknown environment mode '{mode}' (use sample, export, tenable, or none)")


# --------------------------------------------------------------------------- #
# Selection
# --------------------------------------------------------------------------- #

def internet_facing(asset: dict, intake_tags: list[str]) -> tuple[bool, str | None]:
    """Rule order: Tenable exposure field, intake-listed tag, public IPv4."""
    if asset.get("internet_exposed") is True:
        return True, "tenable_exposure_field"
    wanted = {t.strip().lower() for t in intake_tags}
    for tag in asset.get("tags", []):
        combined = f"{tag.get('key', '')}: {tag.get('value', '')}".strip().lower()
        if combined in wanted or tag.get("value", "").strip().lower() in wanted:
            return True, "intake_tag"
    for ip in asset.get("ipv4s", []):
        if _is_public_ipv4(ip):
            return True, "public_ipv4"
    return False, None


def _severity_rank(f: dict) -> int:
    return SEVERITY_ORDER.get(f.get("severity", ""), 0)


def _is_open(f: dict) -> bool:
    return (f.get("state") or "") in OPEN_STATES


def _exploitable(f: dict) -> bool:
    return bool(f.get("kev") or f.get("exploit_available") or (f.get("vpr") or 0) >= 7.0)


def _entry_sort_key(f: dict):
    return (
        0 if f["kev"] else 1,
        -(f["vpr"] or 0.0),
        -(f["epss"] or 0.0),
        -(f["cvss3"] or 0.0),
        -_severity_rank(f),
        f["finding_id"],
    )


def _is_identity_tier(asset: dict) -> tuple[bool, str | None]:
    host = (asset.get("hostname") or "").lower()
    for pat in IDENTITY_HOST_PATTERNS:
        if re.search(pat, host):
            return True, "identity_tier_hostname"
    for sw in asset.get("installed_software", []):
        for pat in IDENTITY_SOFTWARE_PATTERNS:
            if re.search(pat, sw.lower()):
                return True, "identity_tier_software"
    for tag in asset.get("tags", []):
        if tag.get("value", "").strip().lower() in IDENTITY_TAG_VALUES or tag.get("key", "").strip().lower() == "role" and "domain" in tag.get("value", "").lower():
            return True, "identity_tier_tag"
    for st in asset.get("system_types", []):
        if "domain" in st.lower() or "directory" in st.lower():
            return True, "identity_tier_system_type"
    return False, None


def _is_server(asset: dict) -> bool:
    host = (asset.get("hostname") or "").lower()
    dt = (asset.get("device_type") or "").lower()
    os_names = " ".join(asset.get("operating_systems", [])).lower()
    if "endpoint" in host or "laptop" in host or "workstation" in host:
        return False
    if dt in {"endpoint", "workstation", "laptop", "mobile", "printer"}:
        return False
    if "windows 10" in os_names or "windows 11" in os_names or "macos" in os_names:
        return False
    if host.startswith("ot device") or "otsensor" in [s.lower() for s in asset.get("sources", [])]:
        return False
    return True


def _data_match(asset: dict, data_types: list[str]) -> tuple[list[str], str | None]:
    """Return (data types the asset appears to hold, rule that fired)."""
    host = (asset.get("hostname") or "").lower()
    software = " ".join(asset.get("installed_software", [])).lower()
    tag_text = " ".join(f"{t.get('key','')}:{t.get('value','')}" for t in asset.get("tags", [])).lower()
    by_tag: list[str] = []
    by_host: list[str] = []
    by_software: list[str] = []
    for dt in data_types:
        hints = DATA_TYPE_HINTS.get(dt, {"host": [], "software": GENERIC_DB_SOFTWARE, "tag": [dt.lower()]})
        if f"data:{dt.lower()}" in tag_text.replace(" ", "") or any(h in tag_text for h in hints.get("tag", [])):
            by_tag.append(dt)
        elif any(h in host for h in hints.get("host", [])):
            by_host.append(dt)
        elif any(h in software for h in hints.get("software", [])):
            by_software.append(dt)
    # a tag is authoritative; heuristics only speak when no tag names a data type
    if by_tag:
        return by_tag, "tag_match"
    if by_host:
        return by_host, "hostname_heuristic"
    if by_software:
        return by_software, "software_heuristic"
    return [], None


_STORE_HOST_HINTS = ["sql", "db", "database", "oracle", "pacs", "warehouse", "historian", "fs", "file", "share", "nas"]


def _data_store_score(asset: dict) -> int:
    """Tie-breaker when criticality ratings are missing: data stores outrank application tiers."""
    host = (asset.get("hostname") or "").lower()
    software = " ".join(asset.get("installed_software", [])).lower()
    score = 0
    if any(h in host for h in _STORE_HOST_HINTS):
        score += 2
    if any(s in software for s in GENERIC_DB_SOFTWARE):
        score += 2
    return score


def _finding_on(asset_id: str, findings: list[dict]) -> dict | None:
    cands = [f for f in findings if f["asset_id"] == asset_id and _is_open(f)]
    if not cands:
        return None
    cands.sort(key=_entry_sort_key)
    return cands[0]


def _finding_brief(f: dict) -> dict:
    return {
        "finding_id": f["finding_id"],
        "asset": f["hostname"],
        "plugin_id": f["plugin_id"],
        "plugin_name": f["plugin_name"],
        "cve": f["cve"][0] if f["cve"] else None,
        "cves": f["cve"],
        "vpr": f["vpr"],
        "epss": f["epss"],
        "cvss3": f["cvss3"],
        "kev": f["kev"],
        "exploit_available": f["exploit_available"],
        "severity": f["severity"],
        "first_found": f["first_found"],
        "port": f["port"],
        "protocol": f["protocol"],
    }


def select_seed(estate: Estate, intake: dict) -> dict:
    env = intake.get("environment") or {}
    intake_tags = as_list(env.get("internet_facing_tags")) or ["Exposure: Internet"]
    data_types = as_list(intake.get("data_types")) or ["PII"]
    assets_by_id = {a["id"]: a for a in estate.assets}
    assumptions: list[dict] = []

    def assume(text: str) -> str:
        aid = f"A{len(assumptions) + 1}"
        assumptions.append({"id": aid, "text": text})
        return aid

    # --- internet-facing determination per asset
    facing: dict[str, str] = {}
    for a in estate.assets:
        ok, rule = internet_facing(a, intake_tags)
        if ok:
            facing[a["id"]] = rule or "unknown"
    # findings may carry an ipv4 not on the asset table (CSV exports)
    for f in estate.findings:
        if f["asset_id"] not in facing and f.get("ipv4") and _is_public_ipv4(f["ipv4"]):
            facing[f["asset_id"]] = "public_ipv4"

    # --- entry
    entry_cands = [f for f in estate.findings if f["asset_id"] in facing and _is_open(f) and _exploitable(f)]
    entry_cands.sort(key=_entry_sort_key)
    entry: dict
    if entry_cands:
        f = entry_cands[0]
        rule = "kev_internet_facing" if f["kev"] else ("exploit_internet_facing" if f["exploit_available"] else "vpr_internet_facing")
        entry = _finding_brief(f) | {
            "asset_id": f["asset_id"],
            "internet_facing": True,
            "internet_facing_rule": facing[f["asset_id"]],
            "rule": rule,
        }
    else:
        aid = assume("No exploitable finding on an internet-facing asset was found in the data; the entry point is assumed to be a remote-access gateway with an unpatched, publicly known vulnerability.")
        entry = {
            "finding_id": None, "asset_id": None, "asset": "remote access gateway (assumed)", "cve": None, "cves": [],
            "vpr": None, "epss": None, "cvss3": None, "kev": None, "exploit_available": None, "severity": None,
            "first_found": None, "port": None, "protocol": None,
            "internet_facing": True, "internet_facing_rule": None, "rule": "assumption", "assumption": aid,
        }

    # --- pivot
    pivot_cands = []
    for a in estate.assets:
        if a["id"] == entry.get("asset_id"):
            continue
        if not _is_server(a):
            continue
        identity, id_rule = _is_identity_tier(a)
        acr = a.get("acr") or 0.0
        if identity or acr >= 7.0:
            pivot_cands.append((0 if identity else 1, -acr, a["hostname"], a, id_rule or "high_acr_server"))
    pivot_cands.sort(key=lambda t: (t[0], t[1], t[2]))
    # Tenable One attack path data, when present, overrides inference
    path_source = "inferred"
    apa_pivot = None
    for p in estate.attack_paths or []:
        if p.get("entry") == entry.get("asset") and p.get("pivot"):
            apa_pivot = p
            break
    pivot: dict
    if apa_pivot:
        path_source = "tenable_apa"
        pa = next((a for a in estate.assets if a["hostname"] == apa_pivot["pivot"]), None)
        pf = _finding_on(pa["id"], estate.findings) if pa else None
        pivot = {
            "finding_id": pf["finding_id"] if pf else None,
            "asset_id": pa["id"] if pa else None,
            "asset": apa_pivot["pivot"],
            "technique": apa_pivot.get("technique") or "per attack path",
            "rule": "tenable_attack_path",
            "acr": pa.get("acr") if pa else None,
            "cve": pf["cve"][0] if pf and pf["cve"] else None,
        }
    elif pivot_cands:
        _, _, _, pa, rule = pivot_cands[0]
        pf = _finding_on(pa["id"], estate.findings)
        if pf:
            technique = f"exploitation of {pf['cve'][0] if pf['cve'] else pf['plugin_name']} on {pa['hostname']}"
            pivot = {"finding_id": pf["finding_id"], "cve": pf["cve"][0] if pf["cve"] else None, "vpr": pf["vpr"], "kev": pf["kev"]}
        else:
            aid = assume(f"No open finding on {pa['hostname']} supports a specific exploit; the pivot technique is assumed to be credential reuse from the entry host.")
            technique = "credential reuse (assumed)"
            pivot = {"finding_id": None, "cve": None, "vpr": None, "kev": None, "assumption": aid}
        pivot.update({"asset_id": pa["id"], "asset": pa["hostname"], "technique": technique, "rule": rule, "acr": pa.get("acr")})
    else:
        aid = assume("No identity-tier or high-criticality server was found in the data; the pivot is assumed to be the domain controller through credential reuse.")
        pivot = {"finding_id": None, "asset_id": None, "asset": "domain controller (assumed)", "technique": "credential reuse (assumed)",
                 "rule": "assumption", "acr": None, "cve": None, "assumption": aid}

    # --- target (crown jewel)
    target_cands = []
    for a in estate.assets:
        if a["id"] in {entry.get("asset_id"), pivot.get("asset_id")}:
            continue
        matched, rule = _data_match(a, data_types)
        if not matched:
            continue
        target_cands.append((-(a.get("acr") or 0.0), -_data_store_score(a), -(a.get("exposure_score") or 0.0), a["hostname"], a, matched, rule))
    target_cands.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
    target_cands = [(t[0], t[2], t[3], t[4], t[5], t[6]) for t in target_cands]
    target: dict
    if target_cands:
        _, _, _, ta, matched, rule = target_cands[0]
        tf = _finding_on(ta["id"], estate.findings)
        target = {
            "finding_id": tf["finding_id"] if tf else None,
            "asset_id": ta["id"],
            "asset": ta["hostname"],
            "criticality": ta.get("acr"),
            "exposure_score": ta.get("exposure_score"),
            "data": matched,
            "rule": rule,
            "cve": tf["cve"][0] if tf and tf["cve"] else None,
            "operating_systems": ta.get("operating_systems", []),
        }
        if ta.get("acr") is None:
            target["assumption"] = assume(f"{ta['hostname']} has no asset criticality rating in the data; it was chosen by the {rule} rule alone.")
    else:
        aid = assume(f"No asset in the data matched the intake data types {data_types}; the crown jewel is assumed to be the primary database holding {', '.join(data_types)}.")
        target = {"finding_id": None, "asset_id": None, "asset": "primary database (assumed)", "criticality": None,
                  "exposure_score": None, "data": data_types, "rule": "assumption", "cve": None, "assumption": aid}

    cited = [x for x in (entry.get("finding_id"), pivot.get("finding_id"), target.get("finding_id")) if x]
    kev_count = sum(1 for f in estate.findings if f["kev"])
    seed = {
        "schema_version": "1",
        "generated_at": now_iso(),
        "source": estate.source,
        "mode": estate.mode,
        "entry": entry,
        "pivot": pivot,
        "target": target,
        "path_source": path_source,
        "findings_cited": cited,
        "assumptions": assumptions,
        "data_types_requested": data_types,
        "stats": {
            "assets": len(estate.assets),
            "findings": len(estate.findings),
            "internet_facing_assets": len(facing),
            "kev_findings": kev_count,
            "entry_candidates": len(entry_cands),
            "pivot_candidates": len(pivot_cands),
            "target_candidates": len(target_cands),
        },
        "candidates": {
            "entry": [_finding_brief(f) | {"internet_facing_rule": facing.get(f["asset_id"])} for f in entry_cands[:5]],
            "pivot": [{"asset": t[3]["hostname"], "acr": t[3].get("acr"), "rule": t[4]} for t in pivot_cands[:5]],
            "target": [{"asset": t[3]["hostname"], "acr": t[3].get("acr"), "data": t[4], "rule": t[5]} for t in target_cands[:5]],
        },
        "notes": list(estate.notes),
    }
    return seed


def build_seed(intake: dict, **kwargs) -> dict:
    estate = load_estate(intake, **kwargs)
    return select_seed(estate, intake)


def save_estate(estate: Estate, path: str | os.PathLike) -> None:
    """Write a pulled estate to disk (for replay in export mode). Keep it under uploads/."""
    write_json(path, {
        "name": estate.source,
        "saved_at": now_iso(),
        "assets": estate.assets,
        "findings": estate.findings,
        "attack_paths": estate.attack_paths,
    })
