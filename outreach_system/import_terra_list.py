# -*- coding: utf-8 -*-
"""TERRA Google Sheets → master_companies.csv / targets.csv 取り込み"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from google.oauth2.service_account import Credentials
import gspread

BASE_DIR = Path(__file__).resolve().parent
MASTER_PATH = BASE_DIR / "master_companies.csv"
TARGETS_PATH = BASE_DIR / "targets.csv"
CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SHEET_ID = "1LootFV_qe4ZepuRBPBNLaNgjxqqkVj2QJEcGvU8CSBg"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
FIELDNAMES = ["company", "contact_name", "email", "type", "memo"]


def load_sheet() -> list[list[str]]:
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SHEET_ID)
    ws = ss.get_worksheet(0)
    return ws.get_all_values()


def load_existing_companies(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return {row["company"].strip() for row in reader if row.get("company")}


def parse_rows(rows: list[list[str]]) -> list[dict[str, str]]:
    results = []
    for row in rows:
        if not row or not row[0].strip():
            continue
        company = row[0].strip()
        c_col = row[2].strip() if len(row) > 2 else ""
        d_col = row[3].strip() if len(row) > 3 else ""

        email = c_col if EMAIL_RE.match(c_col) else ""
        if not email and EMAIL_RE.match(d_col):
            email = d_col

        row_text = " ".join(row)
        if "元請け" in row_text:
            target_type = "元請け"
        elif "SES" in row_text:
            target_type = "SES"
        else:
            target_type = ""

        results.append(
            {
                "company": company,
                "contact_name": "",
                "email": email,
                "type": target_type,
                "memo": d_col,
            }
        )
    return results


def append_to_csv(new_rows: list[dict[str, str]], path: Path) -> tuple[int, int]:
    existing = load_existing_companies(path)
    added = 0
    skipped = 0
    write_header = not path.exists()

    with path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        for row in new_rows:
            if row["company"] in existing:
                skipped += 1
            else:
                writer.writerow(row)
                existing.add(row["company"])
                added += 1

    return added, skipped


def resolve_output_path(target: str) -> Path:
    if target == "master":
        return MASTER_PATH
    return TARGETS_PATH


def filter_for_target(rows: list[dict[str, str]], target: str) -> list[dict[str, str]]:
    if target == "targets":
        return [r for r in rows if r.get("email")]
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="TERRAリスト取り込み")
    parser.add_argument(
        "--target",
        choices=["master", "targets"],
        default="targets",
        help="master=全件→master_companies.csv / targets=メアドあり→targets.csv",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="取り込みプレビュー（書き込みなし）")
    mode.add_argument("--run", action="store_true", help="本番取り込み")
    args = parser.parse_args()

    out_path = resolve_output_path(args.target)
    print(f"target={args.target} -> {out_path.name}", flush=True)
    print("Google Sheetsからデータを読み込み中...", flush=True)
    rows = load_sheet()
    print(f"取得行数: {len(rows)}", flush=True)

    parsed = parse_rows(rows)
    filtered = filter_for_target(parsed, args.target)
    existing = load_existing_companies(out_path)

    print(f"\n--- 取り込みプレビュー ({len(filtered)}件) ---", flush=True)
    for row in filtered[:20]:
        status = "skip（既存）" if row["company"] in existing else "add"
        email_display = row["email"] or "（メールなし）"
        print(f"[{status}] {row['company']} / {email_display} / {row['type']}", flush=True)
    if len(filtered) > 20:
        print(f"... 他 {len(filtered) - 20} 件", flush=True)

    if args.dry_run:
        add_count = sum(1 for r in filtered if r["company"] not in existing)
        skip_count = len(filtered) - add_count
        print(f"\n[dry-run] 追加予定={add_count}, スキップ={skip_count}", flush=True)
        print("[dry-run] 書き込みは行いません。", flush=True)
        return

    added, skipped = append_to_csv(filtered, out_path)
    print(f"\n取り込み完了: 追加={added}, スキップ（既存重複）={skipped}", flush=True)


if __name__ == "__main__":
    main()
