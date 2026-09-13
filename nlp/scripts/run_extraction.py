#!/usr/bin/env python3
"""Run extraction over the gold set (or any CSV) and write fingerprints.

    PYTHONPATH=src python3 scripts/run_extraction.py --limit 5
    PYTHONPATH=src python3 scripts/run_extraction.py --provider groq
    PYTHONPATH=src python3 scripts/run_extraction.py --cached     # no API calls
    PYTHONPATH=src python3 scripts/run_extraction.py --dry-run    # plan only

`--cached` replays a saved run instead of calling the provider. It exists
because a live demo is the worst possible moment to discover a free-tier quota:
a rate-limited run turns 18 of 20 reports into FAILED records, and the audience
sees an empty dashboard. Extraction is deterministic at temperature 0, so a
replay shows exactly what a live run would have produced.
"""
import argparse, sys, time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from annotation import (                                    # noqa: E402
    partition_usable,
    read_annotations,
    write_annotations,
)
from extraction import Extractor, get_backend                # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default="data/reports.csv")
    ap.add_argument("--gold", default="data/gold/gold.jsonl",
                    help="restrict to the report_ids in this file")
    ap.add_argument("--out", default="data/predictions.jsonl")
    ap.add_argument("--provider", default=None, help="gemini | groq")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=1.0,
                    help="seconds between calls; free tiers rate-limit hard")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore existing output and redo everything")
    ap.add_argument("--cached", action="store_true",
                    help="replay saved fingerprints; never call the provider")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be extracted, call nothing")
    args = ap.parse_args()

    if args.cached and args.fresh:
        sys.exit("--cached and --fresh contradict each other: one replays the "
                 "saved run, the other discards it.")

    df = pd.read_csv(args.reports)
    if args.gold and Path(args.gold).exists():
        wanted = {a.report_id for a in read_annotations(args.gold)}
        df = df[df.REPORT_ID.isin(wanted)]
    if args.limit:
        df = df.head(args.limit)

    # Resume by default. A run that dies at report 8 should not spend the
    # quota re-doing the first seven.
    done = {}
    if not args.fresh and Path(args.out).exists():
        usable, _ = partition_usable(read_annotations(args.out))
        done = {a.report_id: a for a in usable}
        if done and not (args.cached or args.dry_run):
            print(f"resuming — {len(done)} already extracted\n")

    wanted = list(df.REPORT_ID)

    if args.dry_run:
        missing = [r for r in wanted if r not in done]
        print(f"{len(wanted)} report(s) selected")
        print(f"  {len(wanted) - len(missing)} already in {args.out}")
        print(f"  {len(missing)} would be sent to the provider")
        for report_id in missing[:20]:
            print(f"      {report_id}")
        if len(missing) > 20:
            print(f"      ... and {len(missing) - 20} more")
        print("\nnothing was called and nothing was written.")
        return

    if args.cached:
        # Replay only. A cache miss is an error rather than a quiet fallback to
        # the API — the whole point is that this mode cannot spend quota, and a
        # mode that silently starts calling out is not one you can rely on in
        # front of an audience.
        missing = [r for r in wanted if r not in done]
        if missing:
            sys.exit(
                f"--cached: no saved extraction for {len(missing)} of "
                f"{len(wanted)} report(s), e.g. {missing[:3]}.\n"
                f"Run without --cached once to populate {args.out}."
            )
        out = [done[r] for r in wanted]
        print(f"cached replay — {len(out)} report(s), no provider calls\n")
        for i, fp in enumerate(out, 1):
            bars = ", ".join(f"{b.barrier}/{b.failure_mode}"
                             for b in fp.barrier_failures) or "—"
            print(f"[{i}/{len(out)}] {fp.report_id}  "
                  f"{fp.extraction_status.value:8}  {bars}")
        print(f"\nreplayed {len(out)} from {args.out} (file unchanged)")
        return

    backend = get_backend(args.provider)
    extractor = Extractor(backend=backend)
    print(f"{backend.name} / {backend.model_name} — {len(df)} reports\n")

    out = []
    for i, row in enumerate(df.itertuples(), 1):
        if row.REPORT_ID in done:
            out.append(done[row.REPORT_ID])
            continue
        fp = extractor.extract(row.REPORT_ID, row.NARRATIVE)
        out.append(fp)
        bars = ", ".join(f"{b.barrier}/{b.failure_mode}" for b in fp.barrier_failures) or "—"
        print(f"[{i}/{len(df)}] {fp.report_id}  {fp.extraction_status.value:8}  {bars}")
        if fp.notes:
            print(f"          {fp.notes[:110]}")
        if fp.notes and "rate limited" in fp.notes:
            out.pop()   # do not persist a rate-limit failure as a result
            print("\n  quota exhausted — stopping here. What completed is saved;"
                  "\n  re-run to resume, or try --provider gemini.\n")
            break
        if i < len(df):
            time.sleep(args.sleep)

    n = write_annotations(args.out, out)
    print(f"\nwrote {n} to {args.out}")


if __name__ == "__main__":
    main()
