# -*- coding: utf-8 -*-
"""Phase 9A: gBizINFO API で情報通信業×関東/愛知のIT系法人を取得"""
from __future__ import annotations

import argparse
import csv
import urllib.error

from phase9_helpers import (
    FIELDS_9A,
    GBIZ_NAME_KEYWORDS,
    OUT_9A,
    PREFECTURES,
    gbiz_search_page,
    gbiz_token,
    normalize_gbiz_row,
    rate_limit_sleep,
)

CHECKPOINT = OUT_9A.with_suffix(".checkpoint.json")


def _load_checkpoint() -> set[str]:
    if not CHECKPOINT.exists():
        return set()
    import json

    data = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    return set(data.get("done_queries", []))


def _save_checkpoint(done: set[str]) -> None:
    import json

    CHECKPOINT.write_text(
        json.dumps({"done_queries": sorted(done)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_existing() -> dict[str, dict]:
    from crawl_common import read_csv

    out: dict[str, dict] = {}
    for r in read_csv(OUT_9A):
        corp = (r.get("corporate_number") or "").strip()
        if corp:
            out[corp] = r
    return out


def _append_rows(rows: list[dict]) -> None:
    write_header = not OUT_9A.exists()
    with OUT_9A.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS_9A, extrasaction="ignore")
        if write_header:
            w.writeheader()
        for row in rows:
            w.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 9A gBizINFO crawl")
    parser.add_argument("--rate-limit", type=float, default=1.0, help="秒/リクエスト")
    parser.add_argument("--limit-per-query", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        queries = len(PREFECTURES) * len(GBIZ_NAME_KEYWORDS)
        print(
            f"[9A dry-run] queries={queries}, out={OUT_9A.name}, "
            f"prefectures={len(PREFECTURES)}, keywords={GBIZ_NAME_KEYWORDS}",
            flush=True,
        )
        return 0

    token = gbiz_token()
    if not token:
        print(
            "GBIZ_API_TOKEN が未設定です。\n"
            "1) https://info.gbiz.go.jp/ でWeb API利用申請\n"
            "2) メールのURLからトークン取得\n"
            "3) config/.env に GBIZ_API_TOKEN=... を保存\n"
            "詳細: research_results/phase9_api_application_guide.md",
            flush=True,
        )
        return 1

    done_queries = _load_checkpoint()
    merged = _load_existing()
    new_rows: list[dict] = []

    for pref_name, pref_code in PREFECTURES.items():
        for keyword in GBIZ_NAME_KEYWORDS:
            qkey = f"{pref_code}:{keyword}"
            if qkey in done_queries:
                continue

            page = 1
            print(f"[9A] {pref_name} × {keyword} ...", flush=True)
            while True:
                try:
                    data = gbiz_search_page(
                        token=token,
                        name=keyword,
                        prefecture=pref_code,
                        page=page,
                        limit=args.limit_per_query,
                    )
                except urllib.error.HTTPError as e:
                    print(f"[9A] HTTP {e.code} on {qkey} page={page}: {e.reason}", flush=True)
                    if e.code == 401:
                        return 1
                    break
                except Exception as e:
                    print(f"[9A] error on {qkey}: {e}", flush=True)
                    break

                items = data.get("hojin-infos") or data.get("hojin_infos") or []
                if not items:
                    break

                for item in items:
                    row = normalize_gbiz_row(item, prefecture=pref_name, keyword=keyword)
                    if not row:
                        continue
                    corp = row["corporate_number"]
                    if corp not in merged:
                        merged[corp] = row
                        new_rows.append(row)

                if len(items) < args.limit_per_query:
                    break
                page += 1
                rate_limit_sleep(args.rate_limit)

            done_queries.add(qkey)
            _save_checkpoint(done_queries)
            if new_rows:
                _append_rows(new_rows)
                new_rows.clear()
            rate_limit_sleep(args.rate_limit)

    print(f"[9A] {OUT_9A.name}: {len(merged)} companies", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
