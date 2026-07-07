# -*- coding: utf-8 -*-
"""Phase 9C 並列ワーカー出力を統合 → phase9_screening_results.csv"""
from __future__ import annotations

import argparse

from crawl_common import BASE_DIR, read_csv, write_csv
from phase4_helpers import company_core
from phase9_helpers import FIELDS_SCREENING, OUT_SCREENING

OUT = OUT_SCREENING


def part_paths(total: int) -> list:
    return [BASE_DIR / f"phase9c_part{i}.csv" for i in range(1, total + 1)]


def discover_part_files() -> list:
    return sorted(BASE_DIR.glob("phase9c_part*.csv"))


def merge_parts(total: int = 0) -> list[dict]:
    paths = part_paths(total) if total > 0 else discover_part_files()
    if not paths:
        return read_csv(OUT)

    merged: dict[str, dict] = {}
    for path in paths:
        if not path.exists():
            print(f"  skip (missing): {path.name}", flush=True)
            continue
        for r in read_csv(path):
            core = r.get("company_core") or company_core(r.get("company_name", ""))
            if not core:
                continue
            merged[core] = r

    for r in read_csv(OUT):
        core = r.get("company_core") or company_core(r.get("company_name", ""))
        if core and core not in merged:
            merged[core] = r

    return list(merged.values())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--total", type=int, default=0)
    args = parser.parse_args()

    rows = merge_parts(args.total)
    if not rows:
        print("No phase9c part files found.", flush=True)
        return 1

    write_csv(OUT, FIELDS_SCREENING, rows)
    ses = sum(1 for r in rows if r.get("is_ses_company") == "yes")
    mentions = sum(1 for r in rows if r.get("has_incentive_mention") == "yes")
    print(f"{OUT.name}: {len(rows)} rows (SES={ses}, incentive={mentions})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
