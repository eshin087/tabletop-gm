"""ttx command line.

  ttx demo                        build the whole sample exercise in one step and open it
  ttx report                      after the exercise: score the tracker, write the AAR and executive summary
  ttx report --demo               the same reports from synthetic demo responses (for a pitch)
  ttx packs                       list industry packs and their verification status
  ttx flags --industry SLUG       plain-language regulated-status questions for the intake
  ttx ingest-plan DOC... --out    extract uploaded plans to text with section anchors
  ttx seed --intake ... --out     pick the attack path from the exposure data
  ttx clocks --intake ... --out   compute the applicable notification clocks
  ttx outline ... --out           deterministic outline skeleton (exercise_pack draft)
  ttx narrate PACK OVERLAY        apply a narrative overlay (narrative fields only)
  ttx validate KIND FILE          seed | pack | packs | org-plan | outline | exercise-pack
  ttx approve PACK --by NAME      human approval gate: lock the outline
  ttx build PACK --out DIR        every deliverable from the approved pack
  ttx score --pack --tracker      score the decision tracker
  ttx aar --pack --score --out    after-action report from the score

No command here calls a model. Live Tenable mode is the only network call and
it is read-only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .common import read_json, read_yaml, write_json


def _load_env(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def _load_intake(path: str) -> dict:
    data = read_yaml(path) if path.endswith((".yaml", ".yml")) else read_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"intake file {path} is not a mapping")
    return data


def _print_result(result, as_json: bool) -> int:
    if as_json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.summary())
    return 0 if result.ok else 1


# --------------------------------------------------------------------------- #

def cmd_report(args) -> int:
    from .demo import open_folder
    from .report import run_report

    result = run_report(args.pack, args.tracker, args.out, args.narrative, demo=args.demo, responses_path=args.responses)
    for note in result["notes"]:
        print(note)
    if result["demo"]:
        print("DEMO: scoring synthetic responses (samples/demo_responses), not a real exercise.")
    print(f"Exercise: {result['pack']}")
    print(f"Tracker:  {result['tracker']}")
    print(f"\n{result['headline']}")
    print(f"Overall readiness: {result['rating']} ({result['percent']}%)")
    print("\nWhat worked:")
    for r in result["worked"]:
        print(f"  - {r}")
    print("\nLessons learned (what to improve):")
    for r in result["improve"]:
        print(f"  - {r}")
    print("\nWritten:")
    for name, path in result["files"].items():
        print(f"  {name:<26} {path}")
    if args.open and open_folder(result["out"]):
        print("Opened the folder.")
    return 0


def cmd_demo(args) -> int:
    from .demo import open_folder, run_sample, write_guide

    out = Path(args.out)
    print(f"Building the sample exercise into {out} (synthetic data, no network, no model)...")
    result = run_sample(out)
    guide = write_guide(out)
    for name, path in result["files"].items():
        print(f"  {name:<28} {path}")
    print(f"\nSample result: {result['headline']}")
    print(f"Start with {guide}")
    if not args.no_open and open_folder(out):
        print("Opened the folder.")
    return 0


def flags_for_industry(industry: str | None, packs_base=None, states: list[str] | None = None) -> list[dict]:
    """Regulated-status questions that change deadlines, most relevant first.

    Order: flags the industry's own clocks use, then flags from the shared clocks
    (card payments, EU or UK data, critical infrastructure), then flags other packs
    use that the industry commonly shares (only with industry=None: all of them).
    """
    from .common import schemas_dir
    from .packs import list_packs, load_common_clocks, load_pack

    questions = read_yaml(schemas_dir() / "flags.yaml") or {}
    used: dict[str, dict] = {}

    wanted_states = {s.upper() for s in (states or [])}

    def note(flag: str, clock: dict, group: int) -> None:
        clock_states = {str(s).upper() for s in (clock.get("applies_when") or {}).get("states") or []}
        if wanted_states and clock_states and not (clock_states & wanted_states):
            return  # this status only matters in states the organization does not operate in
        entry = used.setdefault(flag, {"flag": flag, "group": group, "clocks": []})
        entry["group"] = min(entry["group"], group)
        entry["clocks"].append(clock.get("name") or clock["id"])

    packs = list_packs(packs_base)
    for slug in packs:
        group = 0 if slug == industry else 2
        for c in load_pack(slug, packs_base).clocks:
            for f in (c.get("applies_when") or {}).get("flags") or []:
                note(f, c, group)
    for c in load_common_clocks(packs_base):
        for f in (c.get("applies_when") or {}).get("flags") or []:
            note(f, c, 1)
    out = []
    for flag, entry in used.items():
        if industry and entry["group"] == 2 and flag not in CROSS_INDUSTRY.get(industry, set()):
            continue
        q = questions.get(flag) or {}
        out.append({"flag": flag, "question": q.get("question"), "why": q.get("why"),
                    "group": entry["group"], "clocks": sorted(set(entry["clocks"]))})
    out.sort(key=lambda e: (e["group"], e["flag"]))
    return out


# statuses from other packs that commonly apply to an industry
CROSS_INDUSTRY = {
    "banking": {"nydfs_licensed"},
    "insurance": {"nonbank_financial_institution"},
    "healthcare": {"nydfs_licensed"},
    "saas_technology": {"fedramp_csp", "operates_federal_system", "bank_service_provider", "business_associate"},
    "retail_ecommerce": {"nydfs_licensed"},
    "manufacturing_ot": {"defense_contractor"},
    "energy_utilities": set(),
    "federal_contractors": {"critical_infrastructure"},
    "public_sector": {"operates_federal_system"},
    "higher_education": {"business_associate"},
}


def cmd_flags(args) -> int:
    states = [s.strip() for s in args.states.split(",")] if args.states else None
    rows = flags_for_industry(args.industry, args.packs_dir, states)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    labels = {0: f"For {args.industry}" if args.industry else "Industry statuses", 1: "For any organization", 2: "Also common"}
    current = None
    for r in rows:
        if r["group"] != current:
            current = r["group"]
            print(f"\n{labels[current]}:")
        print(f"  {r['flag']:<36} {r['question']}")
    return 0


def cmd_packs(args) -> int:
    from .packs import list_packs, load_pack, pack_summary

    rows = [pack_summary(load_pack(s, args.packs_dir)) for s in list_packs(args.packs_dir)]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    print(f"{'pack':<22}{'display name':<46}{'clocks':>7}{'researched':>12}{'reqs':>6}")
    for r in rows:
        print(f"{r['slug']:<22}{r['display_name']:<46}{r['clocks']:>7}{r['researched_clocks']:>12}{r['exercise_requirements']:>6}")
    return 0


def cmd_ingest_plan(args) -> int:
    from .plan_ingest import ingest

    result = ingest(args.documents)
    write_json(args.out, result)
    for d in result["documents"]:
        print(f"{d['id']}: {d['filename']} ({d['format']}, {len(d['sections'])} sections, {d['characters']} characters)")
    print(f"wrote {args.out}")
    return 0


def cmd_seed(args) -> int:
    from .seed_engine import load_estate, save_estate, select_seed
    from .validators import validate_seed

    _load_env()
    intake = _load_intake(args.intake)
    estate = load_estate(intake, mode=args.mode, estate_file=args.estate, assets_file=args.assets)
    seed = select_seed(estate, intake)
    if args.kev_check or args.kev_file:
        from .seed_engine import cross_check_kev, load_kev_catalog

        try:
            catalog, label = load_kev_catalog(args.kev_file)
            cross_check_kev(seed, catalog, label)
            mm = seed["kev_check"]["mismatches"]
            print(f"KEV cross-check against {label}: {len(seed['kev_check']['checked'])} findings checked, {len(mm)} mismatch(es)")
        except OSError as exc:
            seed["kev_check"] = {"source": "cisa_kev_feed", "error": f"feed unreachable: {exc}"}
            print(f"KEV cross-check skipped: feed unreachable ({exc}); scanner KEV flags used as is")
    if args.save:
        Path("uploads").mkdir(exist_ok=True)
        target = Path("uploads") / f"estate_{estate.mode}_{seed['generated_at'][:10]}.json"
        save_estate(estate, target)
        print(f"saved pulled estate to {target} (gitignored)")
    write_json(args.out, seed)
    result = validate_seed(seed)
    e, p, t = seed["entry"], seed["pivot"], seed["target"]
    print(f"source: {seed['source']} ({seed['stats']['assets']} assets, {seed['stats']['findings']} findings)")
    print(f"entry:  {e.get('asset')}  {e.get('cve') or ''}  vpr={e.get('vpr')} kev={e.get('kev')}  rule={e.get('rule')} ({e.get('internet_facing_rule')})")
    print(f"pivot:  {p.get('asset')}  {p.get('technique')}  rule={p.get('rule')}")
    print(f"target: {t.get('asset')}  data={t.get('data')} criticality={t.get('criticality')}  rule={t.get('rule')}")
    print(f"path_source: {seed['path_source']}; findings cited: {seed['findings_cited']}; assumptions: {len(seed['assumptions'])}")
    print(f"wrote {args.out}")
    return _print_result(result, False)


def cmd_clocks(args) -> int:
    from .clock_engine import evaluate

    intake = _load_intake(args.intake)
    incident = None
    if args.incident:
        incident = read_json(args.incident)
    elif args.trigger_at:
        incident = {"trigger_at": args.trigger_at}
    result = evaluate(intake, incident, args.packs_dir)
    write_json(args.out, result)
    for c in result["clocks"]:
        due = c.get("deadline_hours")
        bd = c.get("deadline_business_days")
        when = f"{due} h" if due is not None else (f"{bd} business days" if bd is not None else "no fixed number")
        extra = ""
        if c.get("met") is not None:
            extra = "  MET" if c["met"] else "  MISSED"
        print(f"[{c['tier']:<10}] {c['id']:<44} {when:<18} {c.get('regulator') or ''}{extra}")
    if result["banner"]["show"]:
        print("\n" + result["banner"]["text"])
    print(f"\n{len(result['clocks'])} applicable clock(s), {len(result['excluded'])} excluded; wrote {args.out}")
    return 0


def cmd_outline(args) -> int:
    from .outline import build_outline
    from .validators import validate_exercise_pack

    intake = _load_intake(args.intake)
    seed = read_json(args.seed)
    clocks = read_json(args.clocks)
    org_plan = read_json(args.org_plan) if args.org_plan else None
    pack = build_outline(intake, seed, clocks, org_plan, args.packs_dir)
    write_json(args.out, pack)
    print(f"{pack['title']}: {len(pack['injects'])} injects, {len(pack['clocks'])} clocks, org plan {'present' if org_plan else 'absent'}")
    print(f"wrote {args.out} (not approved; review, then ttx approve)")
    return _print_result(validate_exercise_pack(pack), False)


def cmd_narrate(args) -> int:
    from .outline import apply_narrative
    from .validators import validate_exercise_pack

    pack = read_json(args.file)
    overlay = read_json(args.overlay)
    apply_narrative(pack, overlay)
    result = validate_exercise_pack(pack)
    if not result.ok:
        print(result.summary())
        print("narrative not applied: the result fails validation")
        return 1
    out = args.out or args.file
    write_json(out, pack)
    print(f"applied narrative to {len((overlay.get('injects') or {}))} inject(s); wrote {out} (approval cleared; review, then ttx approve)")
    return _print_result(result, False)


def cmd_validate(args) -> int:
    from . import validators as v

    kind = args.kind
    if kind == "seed":
        return _print_result(v.validate_seed(read_json(args.file)), args.json)
    if kind == "pack":
        return _print_result(v.validate_pack(args.file, args.packs_dir), args.json)
    if kind == "packs":
        results = v.validate_all_packs(args.packs_dir)
        rc = 0
        for r in results:
            if args.json:
                print(json.dumps(r.to_dict(), indent=2))
            else:
                print(r.summary())
            rc = rc or (0 if r.ok else 1)
        return rc
    if kind == "clocks":
        return _print_result(v.validate_clocks_file(args.file), args.json)
    if kind == "org-plan":
        org_plan = read_json(args.file)
        documents = None
        if args.source:
            from .plan_ingest import documents_index, ingest

            documents = documents_index(ingest(args.source))
        elif args.plan_text:
            from .plan_ingest import documents_index

            documents = documents_index(read_json(args.plan_text))
        return _print_result(v.validate_org_plan(org_plan, documents), args.json)
    if kind in {"outline", "exercise-pack"}:
        pack = read_json(args.file)
        return _print_result(v.validate_exercise_pack(pack, require_approval=(kind == "exercise-pack")), args.json)
    raise SystemExit(f"unknown kind {kind}")


def cmd_approve(args) -> int:
    from .outline import stamp_approval
    from .validators import validate_exercise_pack

    pack = read_json(args.file)
    result = validate_exercise_pack(pack)
    if not result.ok:
        print(result.summary())
        print("refusing to approve an outline that fails validation")
        return 1
    stamp_approval(pack, args.by)
    out = args.out or args.file
    write_json(out, pack)
    print(f"approved by {args.by} at {pack['approval']['approved_at']}; hash {pack['approval']['outline_hash'][:12]}; wrote {out}")
    return 0


def cmd_build(args) -> int:
    from .build import build_all

    pack = read_json(args.file)
    only = [s.strip() for s in args.only.split(",")] if args.only else None
    outputs = build_all(pack, args.out, only=only, allow_draft=args.draft)
    for name, path in outputs.items():
        print(f"{name:<20} {path}")
    if getattr(args, "open", False):
        from .demo import open_folder

        if open_folder(args.out):
            print("Opened the folder.")
    return 0


def cmd_score(args) -> int:
    from .score_engine import score_tracker

    pack = read_json(args.pack)
    result = score_tracker(pack, args.tracker, incident_file=args.incident)
    write_json(args.out, result)
    s = result["summary"]
    print(f"headline: {result['headline']}")
    print(f"total {s['total_score']}/{s['max_score']} ({s['percent']}%); injects scored {s['injects_scored']}/{s['injects_total']}")
    for dim, val in s["dimension_averages"].items():
        print(f"  {dim:<28} {val}")
    print(f"gaps: {len(result['gaps'])} ({', '.join(sorted({g['label'] for g in result['gaps']})) or 'none'})")
    print(f"wrote {args.out}")
    return 0


def cmd_aar(args) -> int:
    from .build.aar import build_aar

    pack = read_json(args.pack)
    score = read_json(args.score)
    narrative = read_json(args.narrative) if args.narrative else None
    path = build_aar(pack, score, args.out, narrative=narrative)
    print(f"after_action_report  {path}")
    return 0


# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ttx", description="Tabletop GM engine (deterministic; no model calls)")
    p.add_argument("--version", action="version", version=f"ttx {__version__}")
    p.add_argument("--packs-dir", help="industry packs directory (default: ./skills/industry_packs)")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("report", help="after the exercise: find the filled tracker, score it, write the AAR and executive summary")
    s.add_argument("--pack", help="approved exercise pack (default: out/exercise_pack.json)")
    s.add_argument("--tracker", help="filled tracker .xlsx or decision log .csv (default: newest filled tracker for this exercise)")
    s.add_argument("--narrative", help="optional narrative.json (headline, summary) from the scoring_aar skill")
    s.add_argument("--out", help="output folder (default: out/report, or out/report_demo with --demo)")
    s.add_argument("--demo", action="store_true", help="score synthetic demo responses instead of a filled tracker (for a pitch or practice run)")
    s.add_argument("--responses", help="demo responses YAML (default: samples/demo_responses/responses.yaml)")
    s.add_argument("--open", action="store_true", help="open the folder afterwards")
    s.set_defaults(func=cmd_report)

    s = sub.add_parser("demo", help="build the complete sample exercise in one step and open the folder")
    s.add_argument("--out", default="out/demo")
    s.add_argument("--no-open", action="store_true", help="do not open the folder afterwards")
    s.set_defaults(func=cmd_demo)

    s = sub.add_parser("packs", help="list industry packs")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_packs)

    s = sub.add_parser("flags", help="plain-language regulated-status questions for an industry")
    s.add_argument("--industry", help="pack slug; omit to list every status")
    s.add_argument("--states", help="comma list of US states; drops statuses that only matter elsewhere")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_flags)

    s = sub.add_parser("ingest-plan", help="extract uploaded plans to text with anchors")
    s.add_argument("documents", nargs="+")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_ingest_plan)

    s = sub.add_parser("seed", help="pick the attack path from exposure data")
    s.add_argument("--intake", required=True)
    s.add_argument("--mode", choices=["sample", "export", "tenable", "none"], help="override environment.mode")
    s.add_argument("--estate", help="sample estate JSON or findings export (csv, json, nessus)")
    s.add_argument("--assets", help="optional asset export for export mode")
    s.add_argument("--save", action="store_true", help="write the loaded estate to uploads/ for replay")
    s.add_argument("--kev-check", action="store_true", help="cross-check KEV flags against the public CISA KEV feed (one GET)")
    s.add_argument("--kev-file", help="cross-check against a local copy of the CISA KEV JSON instead (no network)")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_seed)

    s = sub.add_parser("clocks", help="compute applicable notification clocks")
    s.add_argument("--intake", required=True)
    s.add_argument("--incident", help="JSON with trigger_at and notifications {clock_id: iso time}")
    s.add_argument("--trigger-at", help="ISO timestamp when the clocks started")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_clocks)

    s = sub.add_parser("outline", help="deterministic outline skeleton")
    s.add_argument("--intake", required=True)
    s.add_argument("--seed", required=True)
    s.add_argument("--clocks", required=True)
    s.add_argument("--org-plan")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_outline)

    s = sub.add_parser("narrate", help="apply a scenario_design narrative overlay (narrative fields only)")
    s.add_argument("file", help="exercise pack (outline) to update")
    s.add_argument("overlay", help="JSON overlay: injects {I1: {title, what_happens, ...}}, scenario_summary, ...")
    s.add_argument("--out", help="write to a different file (default: in place)")
    s.set_defaults(func=cmd_narrate)

    s = sub.add_parser("validate", help="validate an artifact")
    s.add_argument("kind", choices=["seed", "pack", "packs", "clocks", "org-plan", "outline", "exercise-pack"])
    s.add_argument("file", nargs="?", help="file path, or pack slug for 'pack'")
    s.add_argument("--source", nargs="*", help="org-plan: source documents to verify quotes against")
    s.add_argument("--plan-text", help="org-plan: ingested plan text JSON from ttx ingest-plan")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("approve", help="human approval gate: lock the outline")
    s.add_argument("file")
    s.add_argument("--by", required=True, help="name of the approver")
    s.add_argument("--out", help="write to a different file (default: in place)")
    s.set_defaults(func=cmd_approve)

    s = sub.add_parser("build", help="build every deliverable from the approved exercise pack")
    s.add_argument("file")
    s.add_argument("--out", required=True)
    s.add_argument("--only", help="comma list: deck,guide,handout,tracker,signin,signoff")
    s.add_argument("--draft", action="store_true", help="build from an unapproved outline, watermarked DRAFT")
    s.add_argument("--open", action="store_true", help="open the output folder afterwards")
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("score", help="score the decision tracker")
    s.add_argument("--pack", required=True)
    s.add_argument("--tracker", required=True, help="tracker .xlsx or decision log .csv")
    s.add_argument("--incident", help="JSON with trigger_at and notifications for the clock check")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_score)

    s = sub.add_parser("aar", help="after-action report from a score file")
    s.add_argument("--pack", required=True)
    s.add_argument("--score", required=True)
    s.add_argument("--narrative", help="optional narrative.json from the scoring_aar skill (headline, summary paragraphs)")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_aar)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
