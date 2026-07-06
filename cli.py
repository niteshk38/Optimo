#!/usr/bin/env python3
"""Command-line interface for Optimo.

Examples
--------
  python cli.py search --query "python backend" --location London --resume resume.txt
  python cli.py save --rank 1
  python cli.py tailor --rank 1 --kind cover
  python cli.py track list
  python cli.py track status --job-id <id> --to applied
  python cli.py track export --out applications.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from jobagent.config import Config
from jobagent.models import Job, MatchResult, Profile
from jobagent.pipeline import build_llm, search_and_rank
from jobagent.resume import build_profile, read_resume
from jobagent.tailor import cover_letter, tailored_bullets
from jobagent.tracker import Tracker

CACHE = Path("data/last_results.json")


# --- helpers ---------------------------------------------------------------

def _load_profile(config: Config, resume_path: str | None) -> Profile:
    raw = read_resume(resume_path) if resume_path else ""
    llm = build_llm(config) if raw else None
    return build_profile(raw_text=raw, preferences=config.preferences, llm=llm)


def _cache_results(query: str, profile: Profile, results: list[MatchResult]) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "query": query,
        "profile": asdict(profile),
        "results": [
            {"job": r.job.to_dict(), "score": r.score, "reasons": r.reasons,
             "concerns": r.concerns, "method": r.method}
            for r in results
        ],
    }
    CACHE.write_text(json.dumps(payload, indent=2))


def _load_cache() -> dict:
    if not CACHE.exists():
        sys.exit("No cached search. Run `search` first.")
    return json.loads(CACHE.read_text())


def _job_from_rank(rank: int) -> tuple[Job, dict]:
    data = _load_cache()
    results = data["results"]
    if rank < 1 or rank > len(results):
        sys.exit(f"Rank {rank} out of range (1..{len(results)}).")
    return Job(**results[rank - 1]["job"]), data


# --- commands --------------------------------------------------------------

def cmd_search(args: argparse.Namespace) -> None:
    config = Config.load(args.config)
    profile = _load_profile(config, args.resume)
    results = search_and_rank(
        config, profile, args.query, location=args.location,
        remote=args.remote, use_llm=not args.no_llm,
        limit_per_source=args.limit,
    )
    _cache_results(args.query, profile, results)

    if args.json:
        print(json.dumps([{"score": r.score, **r.job.to_dict()} for r in results], indent=2))
        return

    if not results:
        print("No jobs found. Check your query, sources, or API keys in .env.")
        return

    print(f"\nTop {min(args.top, len(results))} of {len(results)} matches for "
          f"'{args.query}':\n")
    for i, r in enumerate(results[: args.top], start=1):
        print(f"[{i}] {r.score:>5.1f}  {r.job.title}  —  {r.job.company}")
        loc = r.job.location or ("Remote" if r.job.remote else "")
        print(f"        {loc}  ({r.job.source})  {r.job.url}")
        for reason in r.reasons:
            print(f"        + {reason}")
        for concern in r.concerns:
            print(f"        - {concern}")
    print("\nUse `save --rank N` to track one, or `tailor --rank N` to draft an application.")


def cmd_save(args: argparse.Namespace) -> None:
    job, _ = _job_from_rank(args.rank)
    tracker = Tracker(args.db)
    tracker.save_job(job, status=args.status)
    tracker.close()
    print(f"Saved: {job.title} @ {job.company}  (job-id {job.id}, status {args.status})")


def cmd_tailor(args: argparse.Namespace) -> None:
    config = Config.load(args.config)
    job, data = _job_from_rank(args.rank)
    profile = Profile(**data["profile"])
    llm = build_llm(config)
    if not llm.available:
        sys.exit("No LLM reachable. Start Ollama, or set LLM_BASE_URL/LLM_API_KEY in .env.")

    if args.kind == "cover":
        print("\n" + cover_letter(profile, job, llm) + "\n")
    else:
        print(f"\nTailored bullets for {job.title} @ {job.company}:\n")
        for bullet in tailored_bullets(profile, job, llm):
            print(f"  • {bullet}")
        print()


def cmd_track(args: argparse.Namespace) -> None:
    tracker = Tracker(args.db)
    try:
        if args.track_cmd == "list":
            rows = tracker.list(status=args.status)
            if not rows:
                print("No tracked applications yet.")
                return
            for r in rows:
                print(f"  {r['status']:<12} {r['title']}  @  {r['company']}  "
                      f"(id {r['job_id']})")
        elif args.track_cmd == "status":
            ok = tracker.set_status(args.job_id, args.to)
            print("Updated." if ok else f"No application with id {args.job_id}.")
        elif args.track_cmd == "note":
            ok = tracker.add_note(args.job_id, args.text)
            print("Note saved." if ok else f"No application with id {args.job_id}.")
        elif args.track_cmd == "export":
            out = tracker.export_csv(args.out)
            print(f"Exported {len(tracker.list())} rows to {out}")
    finally:
        tracker.close()


# --- parser ----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="optimo", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", help="Path to config.yaml (defaults to project config).")
    p.add_argument("--db", default="data/applications.db", help="Tracker database path.")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="Find and rank jobs.")
    s.add_argument("--query", required=True)
    s.add_argument("--location")
    s.add_argument("--remote", action="store_true")
    s.add_argument("--resume", help="Path to a .txt/.md/.pdf resume.")
    s.add_argument("--limit", type=int, default=25, help="Max results per source.")
    s.add_argument("--top", type=int, default=10, help="How many to display.")
    s.add_argument("--no-llm", action="store_true", help="Keyword ranking only.")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_search)

    sv = sub.add_parser("save", help="Save a ranked result to the tracker.")
    sv.add_argument("--rank", type=int, required=True)
    sv.add_argument("--status", default="saved")
    sv.set_defaults(func=cmd_save)

    t = sub.add_parser("tailor", help="Draft a cover letter or resume bullets.")
    t.add_argument("--rank", type=int, required=True)
    t.add_argument("--kind", choices=["cover", "bullets"], default="cover")
    t.set_defaults(func=cmd_tailor)

    tr = sub.add_parser("track", help="Manage tracked applications.")
    tr_sub = tr.add_subparsers(dest="track_cmd", required=True)
    tl = tr_sub.add_parser("list")
    tl.add_argument("--status")
    ts = tr_sub.add_parser("status")
    ts.add_argument("--job-id", required=True, dest="job_id")
    ts.add_argument("--to", required=True)
    tn = tr_sub.add_parser("note")
    tn.add_argument("--job-id", required=True, dest="job_id")
    tn.add_argument("--text", required=True)
    te = tr_sub.add_parser("export")
    te.add_argument("--out", default="applications.csv")
    tr.set_defaults(func=cmd_track)

    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
