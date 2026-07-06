# -*- coding: utf-8
"""Phase 7D: 粗利%スクリーニング（並列ワーカー対応）"""
from __future__ import annotations

import argparse
import csv
import re
import time
from datetime import date
from math import ceil
from pathlib import Path

from crawl_common import BASE_DIR, read_csv, today_str
from phase4_helpers import company_core, extract_incentive_lines, extract_rate_pct
from phase7_helpers import (
    BingBlockedError,
    fetch_bing_rss_snippets,
    load_existing_surveyed_cores,
    log_error,
    progress_log,
)

MASTER_CSV = BASE_DIR / "ses_company_master_all.csv"
LEGACY_OUT = BASE_DIR / "phase7d_screening_results.csv"
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

INCENTIVE_SNIPPET_HINT = re.compile(r"[%％]|粗利|還元率", re.I)
BLOCK_EXIT_CODE = 2


def part_output_path(part: int) -> Path:
    return BASE_DIR / f"phase7d_part{part}.csv"


def resolve_output(part: int | None) -> Path:
    if part is not None:
        return part_output_path(part)
    return LEGACY_OUT


def split_shard(rows: list[dict], part: int, total: int) -> list[dict]:
    """part は 1-indexed。master を total 等分。"""
    if part < 1 or part > total:
        raise ValueError(f"part must be 1..{total}, got {part}")
    n = len(rows)
    size = ceil(n / total)
    start = (part - 1) * size
    end = min(start + size, n)
    return rows[start:end]


def _load_already_screened(out_csv, part: int | None, total: int) -> set[str]:
    cores: set[str] = set()
    paths = [LEGACY_OUT]
    if part is not None and total > 0:
        paths = [part_output_path(p) for p in range(1, total + 1)]
    for path in paths:
        for r in read_csv(path):
            c = r.get("company_core") or company_core(r.get("company_name", ""))
            if c:
                cores.add(c)
    return cores


def _count_today(out_csv) -> int:
    today = date.today().isoformat()
    return sum(1 for r in read_csv(out_csv) if r.get("screened_date") == today)


def _append_row(out_csv, row: dict) -> None:
    write_header = not out_csv.exists()
    with out_csv.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if write_header:
            w.writeheader()
        w.writerow(row)


def _screen_company(name: str, core: str, worker_part: str) -> dict:
    query = f'"{name}" "SES営業" "粗利" OR "インセンティブ" OR "還元"'
    results = fetch_bing_rss_snippets(query, max_results=5)
    snippets: list[str] = []
    for item in results:
        s = f"{item.get('title', '')} {item.get('snippet', '')}"
        if s.strip():
            snippets.append(s.strip())
    combined = " | ".join(snippets)[:2000]

    has_mention = bool(INCENTIVE_SNIPPET_HINT.search(combined))
    detail = ""
    rate = ""
    if has_mention:
        detail = extract_incentive_lines(combined, limit=500)
        r = extract_rate_pct(combined)
        if r is not None:
            rate = str(r)

    return {
        "company_name": name,
        "company_core": core,
        "bing_snippet": combined,
        "has_incentive_mention": "yes" if has_mention else "no",
        "incentive_detail": detail,
        "incentive_rate": rate,
        "screened_date": today_str(),
        "worker_part": worker_part,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 7D Bing screening (parallel shard support)")
    parser.add_argument("--rate-limit", type=float, default=20.0, help="秒/クエリ")
    parser.add_argument("--daily-limit", type=int, default=0, help="1日あたり上限（0=無制限）")
    parser.add_argument("--limit", type=int, default=0, help="今回の実行上限（0=シャード全件）")
    parser.add_argument("--part", type=int, default=0, help="ワーカー番号（1-indexed）")
    parser.add_argument("--total", type=int, default=1, help="並列ワーカー総数")
    parser.add_argument("--skip-surveyed", action="store_true", default=True)
    args = parser.parse_args()

    part = args.part if args.part > 0 else None
    total = args.total if args.total > 0 else 1
    worker_label = f"part{part}/{total}" if part else "single"
    out_csv = resolve_output(part)

    master = read_csv(MASTER_CSV)
    if not master:
        print(f"{MASTER_CSV.name} not found. Run merge_phase7c.py first.", flush=True)
        return 1

    if part is not None:
        master = split_shard(master, part, total)
        print(f"[7D:{worker_label}] shard size={len(master)} -> {out_csv.name}", flush=True)

    screened = _load_already_screened(out_csv, part, total if part else 0)
    surveyed = load_existing_surveyed_cores() if args.skip_surveyed else set()

    done_today = _count_today(out_csv) if args.daily_limit > 0 else 0
    remaining_daily = max(0, args.daily_limit - done_today) if args.daily_limit > 0 else 0
    run_limit = args.limit if args.limit else (remaining_daily if args.daily_limit > 0 else len(master))

    print(
        f"[7D:{worker_label}] screened={len(screened)}, skip_surveyed={len(surveyed)}, "
        f"run_limit={run_limit}, rate={args.rate_limit}s",
        flush=True,
    )

    processed = 0
    consecutive_errors = 0

    for i, r in enumerate(master, 1):
        if processed >= run_limit:
            print(f"[7D:{worker_label}] limit reached ({processed})", flush=True)
            break

        name = (r.get("company_name") or "").strip()
        core = r.get("company_core") or company_core(name)
        if not name or not core:
            continue
        if core in screened:
            continue
        if core in surveyed:
            screened.add(core)
            continue

        try:
            row = _screen_company(name, core, worker_label)
            _append_row(out_csv, row)
            screened.add(core)
            processed += 1
            consecutive_errors = 0
            if processed % 10 == 0:
                print(f"[7D:{worker_label}] screened {processed}: {name[:40]}", flush=True)
        except BingBlockedError as e:
            log_error(f"phase7d_{worker_label}", name, "BING_BLOCK", str(e))
            print(f"[7D:{worker_label}] Bing blocked — worker stopping: {e}", flush=True)
            return BLOCK_EXIT_CODE
        except Exception as e:
            consecutive_errors += 1
            log_error(f"phase7d_{worker_label}", name, type(e).__name__, str(e))
            if consecutive_errors >= 5:
                print(f"[7D:{worker_label}] 5 consecutive errors — worker stopping", flush=True)
                return BLOCK_EXIT_CODE

        progress_log(i, len(master), f"{worker_label}")
        time.sleep(args.rate_limit)

    total_rows = len(read_csv(out_csv))
    mentions = sum(1 for row in read_csv(out_csv) if row.get("has_incentive_mention") == "yes")
    print(
        f"[7D:{worker_label}] {out_csv.name}: {total_rows} rows ({mentions} incentive mentions)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
