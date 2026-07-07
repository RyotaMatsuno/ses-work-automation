# -*- coding: utf-8 -*-
"""Phase 9B: 国税庁法人番号APIで商号検索"""
from __future__ import annotations

import argparse
import csv
import re
import urllib.error

from crawl_common import today_str
from phase9_helpers import (
    FIELDS_9B,
    NTA_NAME_KEYWORDS,
    OUT_9B,
    nta_app_id,
    nta_name_search,
    parse_nta_corporations,
    rate_limit_sleep,
)

CHECKPOINT = OUT_9B.with_suffix(".checkpoint.json")
SES_NAME_HINT = re.compile(
    r"システム|ソフト|SES|エンジニアリング|技術者派遣|ソリューション|IT|ＩＴ",
    re.I,
)


def _load_checkpoint() -> set[str]:
    if not CHECKPOINT.exists():
        return set()
    import json

    data = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    return set(data.get("done_keywords", []))


def _save_checkpoint(done: set[str]) -> None:
    import json

    CHECKPOINT.write_text(
        json.dumps({"done_keywords": sorted(done)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_existing() -> dict[str, dict]:
    from crawl_common import read_csv

    out: dict[str, dict] = {}
    for r in read_csv(OUT_9B):
        corp = (r.get("corporate_number") or "").strip()
        if corp:
            out[corp] = r
    return out


def _append_rows(rows: list[dict]) -> None:
    write_header = not OUT_9B.exists()
    with OUT_9B.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS_9B, extrasaction="ignore")
        if write_header:
            w.writeheader()
        for row in rows:
            w.writerow(row)


def fetch_keyword(app_id: str, keyword: str) -> list[dict]:
    rows: list[dict] = []
    divide = 1
    divide_size = 1
    while divide <= divide_size:
        root = nta_name_search(app_id=app_id, name=keyword, divide=divide, mode=2)
        chunk, _, divide_size = parse_nta_corporations(root)
        for r in chunk:
            if not SES_NAME_HINT.search(r.get("name", "")):
                continue
            r["search_keyword"] = keyword
            r["source"] = "nta_houjin_bangou"
            r["crawl_date"] = today_str()
            rows.append(r)
        divide += 1
        rate_limit_sleep(1.0)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 9B NTA houjin-bangou crawl")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        print(
            f"[9B dry-run] keywords={NTA_NAME_KEYWORDS}, out={OUT_9B.name}",
            flush=True,
        )
        return 0

    app_id = nta_app_id()
    if not app_id:
        print(
            "NTA_APP_ID が未設定です。\n"
            "1) https://www.houjin-bangou.nta.go.jp/webapi/ から仮登録\n"
            "2) メールのフォームURLから本申請（数日かかる場合あり）\n"
            "3) config/.env に NTA_APP_ID=... を保存\n"
            "詳細: research_results/phase9_api_application_guide.md",
            flush=True,
        )
        return 1

    done = _load_checkpoint()
    merged = _load_existing()
    batch: list[dict] = []

    for keyword in NTA_NAME_KEYWORDS:
        if keyword in done:
            continue
        print(f"[9B] search: {keyword}", flush=True)
        try:
            hits = fetch_keyword(app_id, keyword)
        except urllib.error.HTTPError as e:
            print(f"[9B] HTTP {e.code} for {keyword}: {e.reason}", flush=True)
            if e.code in (401, 403):
                return 1
            continue
        except Exception as e:
            print(f"[9B] error for {keyword}: {e}", flush=True)
            continue

        for r in hits:
            corp = r["corporate_number"]
            if corp not in merged:
                merged[corp] = r
                batch.append(r)

        done.add(keyword)
        _save_checkpoint(done)
        if batch:
            _append_rows(batch)
            batch.clear()

    print(f"[9B] {OUT_9B.name}: {len(merged)} companies", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
