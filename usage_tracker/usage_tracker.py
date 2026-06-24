"""
usage_tracker.py - 日次集計メイン
前日分のcost_log.jsonlを集計してNotionに書き込み、アーカイブに移動する
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "cost_log.jsonl"
ARCHIVE_DIR = BASE_DIR

sys.path.insert(0, str(BASE_DIR.parent))
from usage_tracker.cost_calculator import usd_to_jpy
from usage_tracker.notion_writer import write_cost_record


def load_log() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    records = []
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def save_remaining(records: list[dict]) -> None:
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def archive_records(records: list[dict], ym: str) -> None:
    archive_path = ARCHIVE_DIR / f"cost_log_archive_{ym}.jsonl"
    with open(archive_path, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[usage_tracker] Archived {len(records)} records to {archive_path.name}", flush=True)


def calc_monthly_total(all_records: list[dict], target_ym: str) -> float:
    total = 0.0
    for r in all_records:
        if r.get("ts", "").startswith(target_ym):
            total += usd_to_jpy(r.get("cost_usd", 0))
    return total


def main() -> None:
    target_date = (date.today() - timedelta(days=1)).isoformat()
    target_ym = target_date[:7]  # YYYY-MM
    print(f"[usage_tracker] Aggregating for {target_date}", flush=True)

    all_records = load_log()
    if not all_records:
        print("[usage_tracker] No records found. Exiting.", flush=True)
        return

    # 対象日と残りに分割
    target_records = [r for r in all_records if r.get("ts", "").startswith(target_date)]
    remaining_records = [r for r in all_records if not r.get("ts", "").startswith(target_date)]

    if not target_records:
        print(f"[usage_tracker] No records for {target_date}. Exiting.", flush=True)
        return

    # アーカイブファイルから当月累計を取得
    archive_path = ARCHIVE_DIR / f"cost_log_archive_{target_ym}.jsonl"
    archived_records: list[dict] = []
    if archive_path.exists():
        with open(archive_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        archived_records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    all_month_records = archived_records + target_records

    # script x model 別に集計
    agg: dict[tuple[str, str], dict] = defaultdict(lambda: {"input": 0, "output": 0, "usd": 0.0})
    for r in target_records:
        key = (r["script"], r["model"])
        agg[key]["input"] += r.get("input_tokens", 0)
        agg[key]["output"] += r.get("output_tokens", 0)
        agg[key]["usd"] += r.get("cost_usd", 0.0)

    # Notionに書き込み
    for (script, model), vals in agg.items():
        cost_usd = vals["usd"]
        cost_jpy = usd_to_jpy(cost_usd)
        monthly_total = calc_monthly_total(all_month_records, target_ym)
        write_cost_record(
            date_str=target_date,
            script_name=script,
            model=model,
            input_tokens=vals["input"],
            output_tokens=vals["output"],
            cost_usd=cost_usd,
            cost_jpy=cost_jpy,
            monthly_total_jpy=monthly_total,
        )

    # アーカイブ & ログ更新
    archive_records(target_records, target_ym)
    save_remaining(remaining_records)
    print(f"[usage_tracker] Done. Processed {len(target_records)} records.", flush=True)


if __name__ == "__main__":
    main()
