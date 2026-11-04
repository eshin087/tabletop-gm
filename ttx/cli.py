"""ttx command line.

  ttx packs                       list industry packs and their verification status
  ttx ingest-plan DOC... --out    extract uploaded plans to text with section anchors
  ttx seed --intake ... --out     pick the attack path from the exposure data
  ttx clocks --intake ... --out   compute the applicable notification clocks
  ttx outline ... --out           deterministic outline skeleton (exercise_pack draft)
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
    path = build_aar(pack, score, args.out)
    print(f"after_action_report  {path}")
    return 0


# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ttx", description="Tabletop GM engine (deterministic; no model calls)")
    p.add_argument("--version", action="version", version=f"ttx {__version__}")
    p.add_argument("--packs-dir", help="industry packs directory (default: ./skills/industry_packs)")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("packs", help="list industry packs")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_packs)

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
