# -*- coding: utf-8 -*-
"""qualified_companies から HP 巡回でメアド/フォームURLを取得"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from math import ceil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from enrich_helpers import (
    GOOGLE_RATE_LIMIT_SEC,
    bing_search_hp,
    crawl_for_contacts,
    extract_url_from_memo,
    google_search_hp,
    session,
)

BASE_DIR = Path(__file__).resolve().parent
QUALIFIED_PATH = BASE_DIR / "qualified_companies.csv"
TARGETS_PATH = BASE_DIR / "targets.csv"
STATE_PATH = BASE_DIR / "enrich_state.json"
REPORT_PATH = BASE_DIR / "enrich_report.json"

FIELDS = ["company", "contact_name", "email", "type", "memo"]


def load_qualified(path: Path = QUALIFIED_PATH) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (row.get(k) or "").strip() for k in FIELDS + ["industry_status"]} for row in csv.DictReader(f)]


def load_state(path: Path = STATE_PATH) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict[str, dict], path: Path = STATE_PATH) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_target_companies(path: Path = TARGETS_PATH) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row["company"].strip() for row in csv.DictReader(f) if row.get("company")}


def load_target_emails(path: Path = TARGETS_PATH) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row["email"].strip().lower() for row in csv.DictReader(f) if row.get("email")}


def shard_rows(rows: list[dict], shard_id: int, shard_count: int) -> list[dict]:
    if shard_count <= 1:
        return rows
    size = ceil(len(rows) / shard_count)
    start = shard_id * size
    end = min(start + size, len(rows))
    return rows[start:end]


def select_enrich_targets(
    qualified: list[dict[str, str]],
    state: dict[str, dict],
    target_companies: set[str],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in qualified:
        company = row["company"]
        if not company:
            continue
        if row.get("email"):
            continue
        if company in target_companies:
            continue
        prev = state.get(company, {})
        if prev.get("status") == "done" and (prev.get("found_email") or prev.get("found_form_url")):
            continue
        out.append(row)
    return out


def enrich_company(row: dict[str, str], sess, *, dry_run: bool) -> dict:
    company = row["company"]
    now = datetime.now().isoformat(timespec="seconds")

    memo_url = extract_url_from_memo(row.get("memo", ""))
    hp_url: str | None = memo_url
    last_error: str | None = None

    if not hp_url:
        try:
            hp_url = google_search_hp(company, sess)
            if hp_url:
                time.sleep(GOOGLE_RATE_LIMIT_SEC)
        except Exception as e:
            last_error = str(e)

    if not hp_url:
        try:
            hp_url = bing_search_hp(company, sess)
        except Exception as e:
            last_error = str(e)

    if not hp_url:
        entry = {
            "status": "failed",
            "resolved_url": "",
            "found_email": "",
            "found_form_url": "",
            "attempt_count": 1,
            "last_error": last_error or "hp_not_found",
            "updated_at": now,
        }
        print(f"  [failed] HP not found: {company}", flush=True)
        return entry

    print(f"  HP: {hp_url}", flush=True)
    try:
        resolved, email, form_url = crawl_for_contacts(hp_url, sess, dry_run_log=dry_run)
    except Exception as e:
        entry = {
            "status": "failed",
            "resolved_url": hp_url,
            "found_email": "",
            "found_form_url": "",
            "attempt_count": 1,
            "last_error": str(e),
            "updated_at": now,
        }
        print(f"  [failed] crawl error: {company} — {e}", flush=True)
        return entry

    status = "done" if (email or form_url) else "failed"
    entry = {
        "status": status,
        "resolved_url": resolved or hp_url,
        "found_email": email or "",
        "found_form_url": form_url or "",
        "attempt_count": 1,
        "last_error": None if status == "done" else "no_contact_found",
        "updated_at": now,
    }
    print(
        f"  [{status}] email={email or '-'} form={form_url or '-'}",
        flush=True,
    )
    return entry


def run_enrich(
    *,
    shard_id: int,
    shard_count: int,
    limit: int,
    dry_run: bool,
) -> dict:
    if not QUALIFIED_PATH.exists():
        print(f"{QUALIFIED_PATH.name} not found. Run filter_it_ses.py --run first.", flush=True)
        return {"error": "qualified_missing"}

    qualified = load_qualified()
    state = load_state()
    target_companies = load_target_companies()
    targets = select_enrich_targets(qualified, state, target_companies)
    shard = shard_rows(targets, shard_id, shard_count)
    if limit > 0:
        shard = shard[:limit]

    print(
        f"enrich shard={shard_id}/{shard_count} targets={len(shard)} "
        f"(pool={len(targets)}, qualified={len(qualified)}) dry_run={dry_run}",
        flush=True,
    )

    sess = session()
    stats = {"processed": 0, "success": 0, "failed": 0, "skipped": 0}

    for i, row in enumerate(shard, 1):
        company = row["company"]
        print(f"[{i}/{len(shard)}] {company}", flush=True)

        prev = state.get(company, {})
        attempt = int(prev.get("attempt_count", 0)) + 1

        entry = enrich_company(row, sess, dry_run=dry_run)
        entry["attempt_count"] = attempt
        stats["processed"] += 1
        if entry["status"] == "done":
            stats["success"] += 1
        else:
            stats["failed"] += 1

        if not dry_run:
            state[company] = entry
            save_state(state)

    report = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "dry_run": dry_run,
        "shard_id": shard_id,
        "shard_count": shard_count,
        "limit": limit,
        **stats,
    }
    if not dry_run:
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def export_to_targets(path: Path = TARGETS_PATH) -> tuple[int, int]:
    state = load_state()
    existing_companies = load_target_companies()
    existing_emails = load_target_emails()

    added = 0
    skipped = 0
    fieldnames = FIELDS
    write_header = not path.exists()

    with path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()

        for company, entry in sorted(state.items()):
            if entry.get("status") != "done":
                continue
            email = (entry.get("found_email") or "").strip()
            form_url = (entry.get("found_form_url") or "").strip()
            if not email and not form_url:
                continue
            if company in existing_companies:
                skipped += 1
                continue
            if email and email.lower() in existing_emails:
                skipped += 1
                continue

            memo = ""
            if form_url and not email:
                memo = f"form_url:{form_url}"

            writer.writerow(
                {
                    "company": company,
                    "contact_name": "",
                    "email": email,
                    "type": "",
                    "memo": memo,
                }
            )
            existing_companies.add(company)
            if email:
                existing_emails.add(email.lower())
            added += 1

    return added, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="HP巡回メアド取得")
    parser.add_argument("--shard-id", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0, help="今回の処理上限")
    parser.add_argument("--export-to-targets", action="store_true", help="enrich_state → targets.csv")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()

    if args.export_to_targets:
        added, skipped = export_to_targets()
        print(f"export_to_targets: added={added}, skipped={skipped}", flush=True)
        return 0

    dry_run = not args.run
    report = run_enrich(
        shard_id=args.shard_id,
        shard_count=args.shard_count,
        limit=args.limit,
        dry_run=dry_run,
    )
    if "error" in report:
        return 1

    print(
        f"\nprocessed={report['processed']} success={report['success']} failed={report['failed']}",
        flush=True,
    )
    if dry_run:
        print("[dry-run] enrich_state.json / targets.csv は更新していません。", flush=True)
    else:
        print(f"{STATE_PATH.name} updated", flush=True)
        print(f"{REPORT_PATH.name} written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
