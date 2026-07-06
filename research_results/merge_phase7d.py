# -*- coding: utf-8 -*-
"""Phase 7D 並列ワーカー出力を統合 → phase7d_screening_results.csv"""
from __future__ import annotations

import argparse

from crawl_common import BASE_DIR, read_csv, write_csv
from phase4_helpers import company_core

OUT = BASE_DIR / "phase7d_screening_results.csv"
LEGACY = BASE_DIR / "phase7d_screening_results.csv"

FIELDS = [
    "company_name",
    "company_core",
    "bing_snippet",
    "has_incentive_mention",
    "incentive_detail",
    "incentive_rate",
    "screened_date",
    "worker_part",
]


def part_paths(total: int) -> list:
    return [BASE_DIR / f"phase7d_part{i}.csv" for i in range(1, total + 1)]


def discover_part_files() -> list:
    paths = sorted(BASE_DIR.glob("phase7d_part*.csv"))
    return paths


def merge_parts(total: int = 0) -> list[dict]:
    paths = part_paths(total) if total > 0 else discover_part_files()
    if not paths:
        return read_csv(LEGACY)

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

    # レガシー単一ファイルの行も取り込み（再実行時の重複回避）
    for r in read_csv(LEGACY):
        core = r.get("company_core") or company_core(r.get("company_name", ""))
        if core and core not in merged:
            merged[core] = r

    return list(merged.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge phase7d_part*.csv → phase7d_screening_results.csv")
    parser.add_argument("--total", type=int, default=0, help="期待パート数（0=自動検出）")
    args = parser.parse_args()

    rows = merge_parts(args.total)
    if not rows:
        print("No phase7d part files found.", flush=True)
        return 1

    write_csv(OUT, FIELDS, rows)
    mentions = sum(1 for r in rows if r.get("has_incentive_mention") == "yes")
    print(f"{OUT.name}: {len(rows)} rows ({mentions} incentive mentions)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
