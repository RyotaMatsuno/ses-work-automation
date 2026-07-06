# -*- coding: utf-8 -*-
"""master_companies.csv から SES/IT 企業をフィルタ"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
MASTER_PATH = BASE_DIR / "master_companies.csv"
QUALIFIED_PATH = BASE_DIR / "qualified_companies.csv"
REPORT_PATH = BASE_DIR / "filter_report.json"

INPUT_FIELDS = ["company", "contact_name", "email", "type", "memo"]
OUTPUT_FIELDS = INPUT_FIELDS + ["industry_status"]

POSITIVE_KEYWORDS = [
    "SES",
    "システム",
    "ソフトウェア",
    "ソフト",
    "IT",
    "DX",
    "Web",
    "開発",
    "エンジニア",
    "インフラ",
    "クラウド",
    "AI",
    "SaaS",
    "情報",
    "テクノ",
    "データ",
    "ネットワーク",
    "コンピュータ",
    "コンピューター",
    "プログラム",
    "デジタル",
    "サイバー",
]

NEGATIVE_KEYWORDS = [
    "飲食",
    "居酒屋",
    "建設",
    "不動産",
    "美容",
    "歯科",
    "介護",
    "製造",
    "運送",
    "清掃",
    "小売",
    "農業",
    "医療",
    "病院",
    "保険",
    "証券",
    "銀行",
    "学校",
    "幼稚園",
    "保育",
]


def load_master(path: Path = MASTER_PATH) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [
            {k: (row.get(k) or "").strip() for k in INPUT_FIELDS}
            for row in csv.DictReader(f)
        ]


def classify_row(row: dict[str, str]) -> str:
    text = f"{row.get('company', '')} {row.get('memo', '')}"
    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            return "exclude"
    for kw in POSITIVE_KEYWORDS:
        if kw in text:
            return "include"
    return "review"


def filter_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, int]]:
    qualified: list[dict[str, str]] = []
    counts = {"include": 0, "exclude": 0, "review": 0}

    for row in rows:
        status = classify_row(row)
        counts[status] += 1
        if status in ("include", "review"):
            out = dict(row)
            out["industry_status"] = status
            qualified.append(out)

    return qualified, counts


def write_qualified(rows: list[dict[str, str]], path: Path = QUALIFIED_PATH) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_report(counts: dict[str, int], total: int, *, dry_run: bool) -> None:
    report = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "dry_run": dry_run,
        "total": total,
        "include": counts["include"],
        "exclude": counts["exclude"],
        "review": counts["review"],
        "qualified_output": counts["include"] + counts["review"],
    }
    if not dry_run:
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="SES/IT企業フィルタ")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="件数レポートのみ")
    mode.add_argument("--run", action="store_true", help="qualified_companies.csv を出力")
    args = parser.parse_args()

    if not MASTER_PATH.exists():
        print(f"{MASTER_PATH.name} not found.", flush=True)
        return 1

    rows = load_master()
    qualified, counts = filter_rows(rows)
    dry_run = args.dry_run
    report = write_report(counts, len(rows), dry_run=dry_run)

    print(f"total={report['total']}", flush=True)
    print(f"include={report['include']}, exclude={report['exclude']}, review={report['review']}", flush=True)
    print(f"qualified_output={report['qualified_output']}", flush=True)

    if dry_run:
        print("\n[dry-run] ファイル書き込みは行いません。", flush=True)
        return 0

    write_qualified(qualified)
    print(f"\n{QUALIFIED_PATH.name}: {len(qualified)} rows", flush=True)
    print(f"{REPORT_PATH.name} written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
