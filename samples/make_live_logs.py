"""Write the two scripted live-session logs under samples/live/.

Both are synthetic runs of the sample exercise facilitated in chat: one team that
follows the plan and one that does not. Timestamps are fixed so the files are
reproducible byte for byte and the tests can rebuild and compare them.

    python samples/make_live_logs.py

The tests export each log to a temporary folder and score it. Nothing here calls
a model or the network.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ttx.common import read_json  # noqa: E402
from ttx.decision_log import (  # noqa: E402
    add_clocks, add_decision, add_mark, add_note, edit_decision, save_log, start,
)

PACK = "samples/exercise_pack_sample.json"
DAY = "2026-11-06T"


def _t(hhmm: str) -> str:
    return f"{DAY}{hhmm}:00+00:00"


def good_log(out_dir: Path, pack: dict) -> dict:
    """A team that knows its plan: right owners, inside every commitment, every party told, every clock owned and met."""
    log = start(PACK, out_dir, "Scripted facilitator (synthetic good run)", now=_t("17:00"))
    add_mark(log, pack, "I1", "presented", now=_t("17:02"))
    add_decision(log, pack, "I1", "Treated the session as a suspected SEV1, confirmed it against the firewall logs, opened the incident record, and reached the Incident Commander.",
                 "security_operations", actions="I1-P16,I1-d1,I1-d2", plan_step="yes", documented="yes", scenario_minutes=10, now=_t("17:08"))
    add_mark(log, pack, "I2", "presented", now=_t("17:10"))
    add_decision(log, pack, "I2", "Declared a SEV1, activated the CIRT, and briefed executive leadership, counsel, and the insurer.",
                 "incident_commander", notified="executive_leadership,legal_counsel,cyber_insurer", actions="I2-P35,I2-P17,I2-P18",
                 plan_step="yes", documented="yes", scenario_minutes=20, now=_t("17:18"))
    add_mark(log, pack, "I3", "presented", now=_t("17:20"))
    add_decision(log, pack, "I3", "Isolated the affected segment and kept clinical systems on downtime procedures rather than a full shutdown.",
                 "cio", notified="executive_leadership", actions="I3-P6,I3-P28,I3-P29", plan_step="yes", documented="yes", scenario_minutes=25, now=_t("17:28"))
    add_decision(log, pack, "I3", "Ordered a forced password reset for every privileged account before the restore starts.",
                 "cio", unplanned=True, note="Not in the plan; the room agreed it was worth the disruption.", now=_t("17:29"))
    add_mark(log, pack, "I4", "presented", now=_t("17:30"))
    add_decision(log, pack, "I4", "Will not pay; counsel engages the insurer's negotiator to buy time while recovery proceeds.",
                 "ceo", notified="executive_leadership", actions="I4-P34,I4-P38,I4-P21", plan_step="n/a", documented="yes", now=_t("17:38"))
    add_mark(log, pack, "I5", "presented", now=_t("17:40"))
    add_decision(log, pack, "I5", "Restore in the plan's order: identity, then the EHR database from the offline copy, then clinics.",
                 "cio", notified="executive_leadership", actions="I5-P32,I5-P30,I5-P31", plan_step="yes", documented="yes", now=_t("17:48"))
    add_mark(log, pack, "I6", "presented", now=_t("17:50"))
    add_decision(log, pack, "I6", "Counsel owns every regulatory notice; the Privacy Officer starts the breach risk assessment today.",
                 "general_counsel", notified="hhs_ocr,state_health_department,fbi,cyber_insurer,patients", actions="I6-P26,I6-P25,I6-P23",
                 plan_step="yes", documented="yes", now=_t("17:58"))
    add_clocks(log, pack,
               owners={"state_ca_individual_notice": "privacy_officer", "state_ca_ag_sample_notice": "general_counsel",
                       "ca_health_facility_unauthorized_access_15bd": "privacy_officer", "hipaa_hhs_notice_500_or_more": "privacy_officer",
                       "hipaa_individual_notice": "privacy_officer", "hipaa_media_notice": "communications"},
               planned_hours={"state_ca_individual_notice": 500, "state_ca_ag_sample_notice": 700, "ca_health_facility_unauthorized_access_15bd": 300,
                              "hipaa_hhs_notice_500_or_more": 1000, "hipaa_individual_notice": 1000, "hipaa_media_notice": 1000},
               now=_t("18:00"))
    add_mark(log, pack, "I7", "presented", now=_t("18:02"))
    add_decision(log, pack, "I7", "Communications drafts the holding statement from the template; the CEO approves it after counsel's review.",
                 "ceo", notified="executive_leadership,legal_counsel", actions="I7-P42,I7-P41,I7-P43", plan_step="yes", documented="yes", now=_t("18:10"))
    add_note(log, "Exercise ended. Hot wash begins.", now=_t("18:12"))
    edit_decision(log, pack, 4, "Host",
                  {"decision": "Declared a SEV1, activated the CIRT, and briefed executive leadership, General Counsel, and the cyber insurer within the hour."},
                  now=_t("18:15"))
    save_log(out_dir, log)
    return log


def poor_log(out_dir: Path, pack: dict) -> dict:
    """A team that improvises: wrong owners, slow, few parties told, one inject skipped, one clock missed and others unplanned."""
    log = start(PACK, out_dir, "Scripted facilitator (synthetic poor run)", now=_t("17:00"))
    add_mark(log, pack, "I1", "presented", now=_t("17:02"))
    add_decision(log, pack, "I1", "Parked the alert as another false alarm from the gateway and kept watching.",
                 "cfo", plan_step="no", documented="no", scenario_minutes=40, now=_t("17:27"))
    add_mark(log, pack, "I2", "presented", now=_t("17:30"))
    add_decision(log, pack, "I2", "Called the CIO at home and waited for a call back before telling anyone else.",
                 "other", note="The on-call help desk lead decided.", notified="executive_leadership", actions="I2-P35",
                 plan_step="partial", documented="partial", scenario_minutes=70, now=_t("17:52"))
    add_mark(log, pack, "I3", "presented", now=_t("17:55"))
    add_decision(log, pack, "I3", "Pulled the network to every site at once; nobody told the hospitals first.",
                 "ceo", plan_step="no", documented="no", scenario_minutes=90, now=_t("18:20"))
    add_decision(log, pack, "I3", "Asked the gateway vendor to shut the appliance down remotely.",
                 "other", unplanned=True, note="The help desk lead called the vendor on their own.", now=_t("18:21"))
    add_mark(log, pack, "I4", "presented", now=_t("18:22"))
    add_decision(log, pack, "I4", "Agreed to open a negotiation and see what the attackers want.",
                 "cfo", plan_step="n/a", documented="no", now=_t("18:40"))
    add_mark(log, pack, "I5", "skipped", now=_t("18:41"))
    add_mark(log, pack, "I6", "presented", now=_t("18:42"))
    add_decision(log, pack, "I6", "Communications will tell patients when there is something to say; nobody named the regulators.",
                 "communications", notified="patients", plan_step="no", documented="no", now=_t("19:00"))
    add_clocks(log, pack, owners={"hipaa_media_notice": "communications"},
               planned_hours={"hipaa_media_notice": 1500, "hipaa_individual_notice": 1200}, now=_t("19:02"))
    add_mark(log, pack, "I7", "presented", now=_t("19:03"))
    add_decision(log, pack, "I7", "Told the reporter it was an IT outage.",
                 "other", note="The on-call PR agency answered the call.", plan_step="no", documented="no", now=_t("19:20"))
    add_note(log, "Exercise ended. Hot wash begins.", now=_t("19:22"))
    save_log(out_dir, log)
    return log


def build_logs(base: Path) -> dict[str, Path]:
    pack = read_json(REPO / PACK)
    good_dir = base / "good"
    poor_dir = base / "poor"
    for d in (good_dir, poor_dir):
        d.mkdir(parents=True, exist_ok=True)
        (d / "decision_log.json").unlink(missing_ok=True)
    good_log(good_dir, pack)
    poor_log(poor_dir, pack)
    return {"good": good_dir / "decision_log.json", "poor": poor_dir / "decision_log.json"}


if __name__ == "__main__":
    os.chdir(REPO)
    for name, path in build_logs(REPO / "samples" / "live").items():
        print(f"{name:<5} {path}")
