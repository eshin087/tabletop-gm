"""Generate samples/synthetic_estate.json.

Hand-written, synthetic, and shaped like a Tenable Vulnerability Management
findings export plus an assets export (the field names recorded in
docs/BUILD_SPEC.md section 7). Hostnames follow the lab placeholder style
(endpoint #12, ot device #3, win2019, dc1, sql2016). IP addresses use the
documentation ranges. CVE identifiers are real public identifiers so the KEV
flag means something; everything else is invented.

Run: python samples/make_synthetic_estate.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "synthetic_estate.json"


def asset(aid, hostnames, ipv4s, acr, exposure=None, tags=None, os_=None, software=None, system_types=None,
          device_type="general-purpose", sources=("NESSUS_AGENT",), fqdns=None, **extra):
    a = {
        "id": aid,
        "hostnames": hostnames,
        "fqdns": fqdns or [f"{hostnames[0].replace(' #', '-')}.vrhs.example" for _ in [0]],
        "ipv4s": ipv4s,
        "ratings": {"acr": {"score": acr}},
        "tags": tags or [],
        "system_types": system_types or ["general-purpose"],
        "operating_systems": [os_ or "Microsoft Windows Server 2019 Standard"],
        "installed_software": software or [],
        "device_type": device_type,
        "sources": [{"name": s} for s in sources],
    }
    if exposure is not None:
        a["exposure_score"] = exposure
    a.update(extra)
    return a


def finding(fid, a, plugin_id, name, cves, severity, vpr=None, epss=None, kev=False, exploit=False, cvss3=None,
            state="OPEN", first="2026-09-14T03:12:00Z", port=0, proto="TCP", source="NESSUS_AGENT"):
    return {
        "finding_id": fid,
        "asset": {
            "uuid": a["id"],
            "hostname": a["hostnames"][0],
            "fqdn": a["fqdns"][0],
            "ipv4": a["ipv4s"][0] if a["ipv4s"] else None,
            "device_type": a["device_type"],
            "operating_system": a["operating_systems"][0],
        },
        "plugin": {
            "id": plugin_id,
            "name": name,
            "cve": cves,
            "vpr": {"score": vpr, "on_cisa_kev": kev},
            "epss_score": epss,
            "exploit_available": exploit,
            "cvss3_base_score": cvss3,
        },
        "severity": severity,
        "state": state,
        "first_found": first,
        "last_found": "2026-11-02T22:40:00Z",
        "port": {"port": port, "protocol": proto},
        "source": source,
    }


assets = []
findings = []

# Internet-facing edge (documentation range 203.0.113.0/24)
vpngw01 = asset("a-0001", ["vpngw01"], ["203.0.113.10", "10.20.0.10"], 8, exposure=812,
                tags=[{"key": "Exposure", "value": "Internet"}, {"key": "Role", "value": "Remote Access"}],
                os_="Ivanti Connect Secure 22.7", device_type="firewall", sources=("NESSUS_SCAN",),
                software=["cpe:/a:ivanti:connect_secure:22.7"])
win2019 = asset("a-0002", ["win2019"], ["203.0.113.22", "10.20.0.22"], 7, exposure=740,
                tags=[{"key": "Exposure", "value": "Internet"}],
                software=["cpe:/a:microsoft:exchange_server:2019", "cpe:/a:microsoft:iis:10.0"], sources=("NESSUS_SCAN", "NESSUS_AGENT"))
portal01 = asset("a-0003", ["patientportal01"], ["203.0.113.40", "10.20.0.40"], 7, exposure=655,
                 tags=[{"key": "Exposure", "value": "Internet"}], os_="Ubuntu 22.04",
                 software=["cpe:/a:apache:http_server:2.4.57", "cpe:/a:openssl:openssl:3.0.2"])
assets += [vpngw01, win2019, portal01]

# Identity and core servers
dc1 = asset("a-0010", ["dc1"], ["10.20.1.5"], 9, tags=[{"key": "Role", "value": "Domain Controller"}],
            software=["cpe:/a:microsoft:active_directory_domain_services"], system_types=["general-purpose"])
dc2 = asset("a-0011", ["dc2"], ["10.20.1.6"], 9, tags=[{"key": "Role", "value": "Domain Controller"}],
            software=["cpe:/a:microsoft:active_directory_domain_services"])
sql2016 = asset("a-0020", ["sql2016"], ["10.20.2.15"], 9, exposure=590,
                tags=[{"key": "Data", "value": "PHI"}, {"key": "System", "value": "EHR database"}],
                os_="Microsoft Windows Server 2016 Standard", software=["cpe:/a:microsoft:sql_server:2016:sp3"])
target2 = asset("a-0021", ["target2"], ["10.20.2.16"], 9, exposure=560,
                tags=[{"key": "Data", "value": "PHI"}, {"key": "System", "value": "Clinical file share"}],
                software=["cpe:/a:microsoft:windows_server:2019"])
ehrapp01 = asset("a-0022", ["ehr-app01"], ["10.20.2.20"], 8, tags=[{"key": "System", "value": "EHR application"}],
                 os_="Red Hat Enterprise Linux 8.9", software=["cpe:/a:apache:log4j:2.14.1", "cpe:/a:oracle:jdk:11.0"])
pacs01 = asset("a-0023", ["pacs01"], ["10.20.2.30"], 8, tags=[{"key": "Data", "value": "PHI"}, {"key": "System", "value": "PACS"}],
               software=["cpe:/a:microsoft:sql_server:2017"])
fileshare01 = asset("a-0024", ["fs01"], ["10.20.2.40"], 6, tags=[{"key": "Data", "value": "PII"}])
revcycle01 = asset("a-0025", ["revcycle01"], ["10.20.2.50"], 7, tags=[{"key": "Data", "value": "PCI"}, {"key": "System", "value": "Revenue cycle"}],
                   software=["cpe:/a:microsoft:sql_server:2019"])
mail01 = asset("a-0026", ["mail01"], ["10.20.2.60"], 6, software=["cpe:/a:microsoft:exchange_server:2019"])
win2008 = asset("a-0027", ["win2008-lab"], ["10.20.3.90"], 3, os_="Microsoft Windows Server 2008 R2")
hvhost01 = asset("a-0028", ["hvhost01"], ["10.20.1.50"], 8, system_types=["hypervisor"], software=["cpe:/a:vmware:esxi:7.0"])
assets += [dc1, dc2, sql2016, target2, ehrapp01, pacs01, fileshare01, revcycle01, mail01, win2008, hvhost01]

# Cloud
aws1 = asset("a-0030", ["ip-10-40-1-12"], ["10.40.1.12"], 5, os_="Amazon Linux 2023", sources=("AWS",),
             aws_ec2_instance_id="i-0a1b2c3d4e5f67890", aws_region="us-west-2")
aws2 = asset("a-0031", ["ip-10-40-1-13"], ["10.40.1.13"], 5, os_="Amazon Linux 2023", sources=("AWS",),
             aws_ec2_instance_id="i-0a1b2c3d4e5f67891", aws_region="us-west-2")
az1 = asset("a-0032", ["vrhs-analytics-vm"], ["10.50.1.4"], 6, os_="Ubuntu 22.04", sources=("AZURE",),
            azure_resource_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-analytics/providers/Microsoft.Compute/virtualMachines/vrhs-analytics-vm",
            azure_vm_id="00000000-0000-0000-0000-000000000001")
assets += [aws1, aws2, az1]

# Endpoints
for i in range(1, 21):
    assets.append(asset(f"a-01{i:02d}", [f"endpoint #{i}"], [f"10.20.{10 + i // 10}.{(i % 250) + 1}"], 2,
                        os_="Microsoft Windows 11 Enterprise", device_type="endpoint"))
# OT and medical devices from the OT sensor
for i in range(1, 9):
    assets.append(asset(f"a-02{i:02d}", [f"ot device #{i}"], [f"10.60.0.{i + 10}"], 7,
                        tags=[{"key": "Segment", "value": "Clinical devices"}], os_="Embedded", device_type="ot",
                        system_types=["medical-device"], sources=("OTSensor",), software=[]))

# Findings. Entry candidates on internet-facing assets:
findings += [
    finding("F1042", vpngw01, 214055, "Ivanti Connect Secure stack-based buffer overflow (CVE-2025-0282)", ["CVE-2025-0282"],
            "critical", vpr=9.6, epss=0.92, kev=True, exploit=True, cvss3=9.0, port=443, source="NESSUS_SCAN"),
    finding("F1043", vpngw01, 209783, "Ivanti Connect Secure outdated version", [], "high", vpr=6.1, epss=0.01, port=443, source="NESSUS_SCAN"),
    finding("F1101", win2019, 152854, "Microsoft Exchange Server remote code execution (ProxyShell, CVE-2021-34473)", ["CVE-2021-34473"],
            "critical", vpr=9.2, epss=0.97, kev=True, exploit=True, cvss3=9.8, port=443, source="NESSUS_SCAN"),
    finding("F1102", win2019, 156003, "Microsoft IIS missing security update", ["CVE-2022-21907"], "critical",
            vpr=7.4, epss=0.30, kev=False, exploit=True, cvss3=9.8, port=80),
    finding("F1201", portal01, 165901, "OpenSSL 3.0.x multiple vulnerabilities", ["CVE-2022-3602", "CVE-2022-3786"], "high",
            vpr=5.9, epss=0.05, cvss3=7.5, port=443),
]
# Internal, higher CVSS, KEV, but not internet-facing (the seed test says entry must still be vpngw01):
findings += [
    finding("F2001", ehrapp01, 155999, "Apache Log4j remote code execution (Log4Shell, CVE-2021-44228)", ["CVE-2021-44228"],
            "critical", vpr=9.9, epss=0.98, kev=True, exploit=True, cvss3=10.0, port=8080),
    finding("F2210", dc1, 141462, "Netlogon elevation of privilege (Zerologon, CVE-2020-1472)", ["CVE-2020-1472"],
            "critical", vpr=9.0, epss=0.96, kev=True, exploit=True, cvss3=10.0, port=445),
    finding("F2211", dc2, 141462, "Netlogon elevation of privilege (Zerologon, CVE-2020-1472)", ["CVE-2020-1472"],
            "critical", vpr=9.0, epss=0.96, kev=True, exploit=True, cvss3=10.0, port=445),
    finding("F2301", sql2016, 181040, "Microsoft SQL Server 2016 SP3 missing cumulative update", ["CVE-2023-36728"],
            "high", vpr=6.7, epss=0.02, kev=False, exploit=False, cvss3=5.5, port=1433),
    finding("F2302", target2, 160000, "SMB signing not required", [], "medium", vpr=4.4, epss=0.0, port=445),
    finding("F2401", pacs01, 181040, "Microsoft SQL Server 2017 missing cumulative update", ["CVE-2023-36728"],
            "high", vpr=6.7, epss=0.02, cvss3=5.5, port=1433),
    finding("F2501", win2008, 125313, "Microsoft RDP remote code execution (BlueKeep, CVE-2019-0708)", ["CVE-2019-0708"],
            "critical", vpr=9.1, epss=0.95, kev=True, exploit=True, cvss3=9.8, port=3389),
    finding("F2601", hvhost01, 171600, "VMware ESXi heap overflow (CVE-2021-21974)", ["CVE-2021-21974"], "high",
            vpr=8.4, epss=0.90, kev=True, exploit=True, cvss3=8.8, port=427),
    finding("F2701", mail01, 152854, "Microsoft Exchange Server remote code execution (ProxyShell, CVE-2021-34473)", ["CVE-2021-34473"],
            "critical", vpr=9.2, epss=0.97, kev=True, exploit=True, cvss3=9.8, port=443),
    finding("F2801", revcycle01, 181040, "Microsoft SQL Server 2019 missing cumulative update", ["CVE-2023-36728"],
            "high", vpr=6.7, epss=0.02, cvss3=5.5, port=1433),
    # a fixed finding that must be ignored
    finding("F2901", portal01, 214055, "Ivanti Connect Secure stack-based buffer overflow (CVE-2025-0282)", ["CVE-2025-0282"],
            "critical", vpr=9.6, epss=0.92, kev=True, exploit=True, cvss3=9.0, state="FIXED", port=443),
]
n = 3000
for i, a in enumerate(assets):
    if a["device_type"] == "endpoint":
        n += 1
        findings.append(finding(f"F{n}", a, 190000 + (i % 7), "Microsoft Windows 11 missing cumulative update", ["CVE-2024-30088"],
                                "high", vpr=6.9, epss=0.12, kev=(i % 5 == 0), exploit=True, cvss3=7.0))
    if a["device_type"] == "ot":
        n += 1
        findings.append(finding(f"F{n}", a, 500100 + (i % 3), "Embedded device uses default credentials", [], "critical",
                                vpr=7.3, epss=None, kev=False, exploit=True, cvss3=9.8, source="OTSensor", port=502))

estate = {
    "name": "Valley Regional Health System synthetic estate",
    "description": "Synthetic. Shaped like a Tenable VM findings export plus an assets export. No real hosts, no real data.",
    "generated_by": "samples/make_synthetic_estate.py",
    "assets": assets,
    "findings": findings,
    "attack_paths": [],
}

OUT.write_text(json.dumps(estate, indent=2) + "\n", encoding="utf-8", newline="\n")
print(f"wrote {OUT} with {len(assets)} assets and {len(findings)} findings")
