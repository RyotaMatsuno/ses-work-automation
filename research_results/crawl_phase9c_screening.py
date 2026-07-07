# -*- coding: utf-8 -*-
"""Phase 9C-2: 改良版Bingスクリーニング（SES判定→インセンティブ検索の2段階）"""
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
from phase7_helpers import BingBlockedError, fetch_bing_rss_snippets, log_error, progress_log
from phase9_helpers import FIELDS_SCREENING, OUT_NEW, OUT_SCREENING, ses_signal_from_snippets

LEGACY_OUT = OUT_SCREENING
BLOCK_EXIT_CODE = 2

INCENTIVE_SNIPPET_HINT = re.compile(r"[%％]|粗利|還元率|インセンティブ|歩合", re.I)


def part_output_path(part: int) -> Path:
    return BASE_DIR / f"phase9c_part{part}.csv"


def resolve_output(part: int | None) -> Path:
    if part is not None:
        return part_output_path(part)
    return LEGACY_OUT


def split_shard(rows: list[dict], part: int, total: int) -> list[dict]:
    if part < 1 or part > total:
        raise ValueError(f"part must be 1..{total}, got {part}")
    n = len(rows)
    size = ceil(n / total)
    start = (part - 1) * size
    end = min(start + size, n)
    return rows[start:end]


def _load_already_screened(part: int | None, total: int) -> set[str]:
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


def _count_today(out_csv: Path) -> int:
    today = date.today().isoformat()
    return sum(1 for r in read_csv(out_csv) if r.get("screened_date") == today)


def _append_row(out_csv: Path, row: dict) -> None:
    write_header = not out_csv.exists()
    with out_csv.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS_SCREENING, extrasaction="ignore")
        if write_header:
            w.writeheader()
        w.writerow(row)


def _snippets_from_query(query: str) -> list[str]:
    results = fetch_bing_rss_snippets(query, max_results=5)
    snippets: list[str] = []
    for item in results:
        s = f"{item.get('title', '')} {item.get('snippet', '')}"
        if s.strip():
            snippets.append(s.strip())
    return snippets


def _screen_company(name: str, core: str, corp_num: str, worker_part: str) -> dict:
    ses_query = f'"{name}" SES'
    ses_snippets = _snippets_from_query(ses_query)
    ses_combined = " | ".join(ses_snippets)[:1500]
    is_ses = ses_signal_from_snippets(ses_snippets)

    incentive_combined = ""
    has_mention = "no"
    detail = ""
    rate = ""

    if is_ses:
        inc_query = f'"{name}" "営業" "粗利" OR "インセンティブ" OR "還元"'
        inc_snippets = _snippets_from_query(inc_query)
        incentive_combined = " | ".join(inc_snippets)[:2000]
        has_mention = "yes" if INCENTIVE_SNIPPET_HINT.search(incentive_combined) else "no"
        if has_mention == "yes":
            detail = extract_incentive_lines(incentive_combined, limit=500)
            r = extract_rate_pct(incentive_combined)
            if r is not None:
                rate = str(r)

    return {
        "company_name": name,
        "company_core": core,
        "corporate_number": corp_num,
        "is_ses_company": "yes" if is_ses else "no",
        "bing_snippet_ses": ses_combined,
        "bing_snippet": incentive_combined,
        "has_incentive_mention": has_mention,
        "incentive_detail": detail,
        "incentive_rate": rate,
        "screened_date": today_str(),
        "worker_part": worker_part,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 9C Bing screening (2-stage)")
    parser.add_argument("--rate-limit", type=float, default=20.0, help="秒/クエリ")
    parser.add_argument("--daily-limit", type=int, default=500, help="1日あたり上限")
    parser.add_argument("--limit", type=int, default=0, help="今回の実行上限（0=シャード全件）")
    parser.add_argument("--part", type=int, default=0, help="ワーカー番号（1-indexed）")
    parser.add_argument("--total", type=int, default=1, help="並列ワーカー総数")
    args = parser.parse_args()

    part = args.part if args.part > 0 else None
    total = args.total if args.total > 0 else 1
    worker_label = f"part{part}/{total}" if part else "single"
    out_csv = resolve_output(part)

    master = read_csv(OUT_NEW)
    if not master:
        print(f"{OUT_NEW.name} not found or empty. Run merge_phase9.py first.", flush=True)
        return 1

    if part is not None:
        master = split_shard(master, part, total)
        print(f"[9C:{worker_label}] shard size={len(master)} -> {out_csv.name}", flush=True)

    screened = _load_already_screened(part, total if part else 0)
    done_today = _count_today(out_csv) if args.daily_limit > 0 else 0
    remaining_daily = max(0, args.daily_limit - done_today) if args.daily_limit > 0 else 0
    run_limit = args.limit if args.limit else (remaining_daily if args.daily_limit > 0 else len(master))

    print(
        f"[9C:{worker_label}] screened={len(screened)}, run_limit={run_limit}, "
        f"rate={args.rate_limit}s",
        flush=True,
    )

    processed = 0
    consecutive_errors = 0

    for i, r in enumerate(master, 1):
        if processed >= run_limit:
            print(f"[9C:{worker_label}] limit reached ({processed})", flush=True)
            break

        name = (r.get("company_name") or "").strip()
        core = r.get("company_core") or company_core(name)
        corp = (r.get("corporate_number") or "").strip()
        if not name or not core:
            continue
        if core in screened:
            continue

        try:
            row = _screen_company(name, core, corp, worker_label)
            _append_row(out_csv, row)
            screened.add(core)
            processed += 1
            consecutive_errors = 0
            if processed % 10 == 0:
                print(f"[9C:{worker_label}] screened {processed}: {name[:40]}", flush=True)
            sleep_count = 2 if row.get("is_ses_company") == "yes" else 1
        except BingBlockedError as e:
            log_error(f"phase9c_{worker_label}", name, "BING_BLOCK", str(e))
            print(f"[9C:{worker_label}] Bing blocked — worker stopping: {e}", flush=True)
            return BLOCK_EXIT_CODE
        except Exception as e:
            consecutive_errors += 1
            log_error(f"phase9c_{worker_label}", name, type(e).__name__, str(e))
            if consecutive_errors >= 5:
                print(f"[9C:{worker_label}] 5 consecutive errors — worker stopping", flush=True)
                return BLOCK_EXIT_CODE
            sleep_count = 1

        progress_log(i, len(master), worker_label)
        time.sleep(args.rate_limit * sleep_count)

    total_rows = len(read_csv(out_csv))
    ses_yes = sum(1 for row in read_csv(out_csv) if row.get("is_ses_company") == "yes")
    print(
        f"[9C:{worker_label}] {out_csv.name}: {total_rows} rows ({ses_yes} SES)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
