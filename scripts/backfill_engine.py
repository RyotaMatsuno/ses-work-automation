# -*- coding: utf-8 -*-
"""R5 backfill engine: dry-run / execute with batch logging and rollback support."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES_WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SES_WORK))

from extractors.location_extractor import extract_location
from extractors.rate_extractor import extract_rate, validate_rate_man
from extractors.remote_extractor import extract_remote
from scripts.merge_policy import ALLOWED_OVERWRITE_REASONS, should_update

CASE_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1/"
LOG_DIR = SES_WORK / "backfill_logs"
PROCESSED_DB = SES_WORK / "matching_v3" / "matching_v3_processed.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _load_token() -> str:
    env_path = SES_WORK / "config" / ".env"
    env = dict(dotenv_values(env_path, encoding="utf-8"))
    env.update({k: v for k, v in os.environ.items() if v})
    token = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN", "")
    if not token:
        raise SystemExit(f"NOTION_API_KEY not set ({env_path})")
    return token


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _rt(prop: dict | None) -> str:
    if not prop or prop.get("type") != "rich_text":
        return ""
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


def _title(prop: dict | None) -> str:
    if not prop or prop.get("type") != "title":
        return ""
    return "".join(t.get("plain_text", "") for t in prop.get("title", []))


def _num(prop: dict | None) -> float | None:
    if not prop or prop.get("type") != "number":
        return None
    return prop.get("number")


def _sel(prop: dict | None) -> str | None:
    if not prop or prop.get("type") != "select":
        return None
    sel = prop.get("select")
    return sel.get("name") if sel else None


def _fetch_error_case_ids(db_path: Path, limit: int | None = None) -> list[str]:
    if not db_path.exists():
        logger.warning("processed DB not found: %s", db_path)
        return []
    conn = sqlite3.connect(db_path)
    try:
        query = """
            SELECT case_id
            FROM processed_cases
            WHERE business_status = 'ERROR'
            ORDER BY updated_at ASC
        """
        if limit:
            query += f" LIMIT {int(limit)}"
        rows = conn.execute(query).fetchall()
        return [row[0] for row in rows if row and row[0]]
    finally:
        conn.close()


def _query_pages(
    token: str,
    *,
    page_ids: list[str] | None = None,
    limit: int | None = None,
    status_filter: str | None = None,
) -> list[dict]:
    if page_ids:
        pages = []
        for pid in page_ids:
            resp = requests.get(f"{NOTION_BASE}pages/{pid}", headers=_headers(token), timeout=30)
            if resp.status_code == 404:
                logger.warning("Page not found: %s", pid)
                continue
            resp.raise_for_status()
            pages.append(resp.json())
            time.sleep(0.1)
        return pages[:limit] if limit else pages

    results: list[dict] = []
    cursor: str | None = None
    while True:
        notion_filter: dict[str, Any] = {"property": "ステータス", "select": {"equals": "募集中"}}
        body: dict[str, Any] = {
            "page_size": 100,
            "filter": notion_filter,
        }
        if cursor:
            body["start_cursor"] = cursor
        resp = requests.post(
            f"{NOTION_BASE}databases/{CASE_DB_ID}/query",
            headers=_headers(token),
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))
        if limit and len(results) >= limit:
            return results[:limit]
        cursor = data.get("next_cursor")
        if not data.get("has_more") or not cursor:
            break
        time.sleep(0.25)
    return results


def _extract_fields(text: str, fields: set[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    rate = extract_rate(text) if "rate" in fields else None
    remote = extract_remote(text) if "remote" in fields else None
    location = extract_location(text) if "location" in fields else None

    if rate:
        out["rate_type"] = rate.rate_type
        out["extraction_method"] = rate.method
        out["extraction_confidence"] = int(rate.confidence * 100)
        out["needs_review"] = rate.needs_review
        if rate.rate_max_man is not None:
            out["単価（万円）"] = validate_rate_man(rate.rate_max_man)
        elif rate.rate_type == "not_present":
            out["単価（万円）"] = None
        out["_rate_confidence"] = rate.confidence

    if remote:
        out["remote_type"] = remote.remote_type
        out["_remote_confidence"] = remote.confidence

    if location and location.location:
        out["勤務地"] = location.location
        out["_location_confidence"] = location.confidence

    out["pipeline_version"] = "v2"
    return out


def _should_skip_for_only_empty(field: str, old_val) -> bool:
    if field == "単価（万円）" and isinstance(old_val, (int, float)) and (old_val > 200 or old_val == 0):
        return False
    if field == "rate_type" and old_val == "skill_dependent_no_number":
        return False
    return old_val not in (None, "", 0)


def _build_changes(props: dict, extracted: dict[str, Any], *, only_empty: bool) -> list[dict[str, Any]]:
    changes: list[dict] = []
    old_rate_conf = (_num(props.get("extraction_confidence")) or 0) / 100.0

    field_map = [
        ("rate_type", "rate_type", extracted.get("_rate_confidence", 0.5)),
        ("remote_type", "remote_type", extracted.get("_remote_confidence", 0.5)),
        ("勤務地", "勤務地", extracted.get("_location_confidence", 0.5)),
        ("単価（万円）", "単価（万円）", extracted.get("_rate_confidence", 0.5)),
        ("extraction_method", "extraction_method", 0.5),
        ("extraction_confidence", "extraction_confidence", 0.5),
        ("pipeline_version", "pipeline_version", 0.5),
        ("needs_review", "needs_review", 0.5),
    ]

    for notion_field, key, conf in field_map:
        if key not in extracted:
            continue
        new_val = extracted[key]
        prop = props.get(notion_field) or {}
        ptype = prop.get("type")
        if ptype == "number":
            old_val = prop.get("number")
        elif ptype == "select":
            old_val = _sel(prop)
        elif ptype == "rich_text":
            old_val = _rt(prop)
        elif ptype == "checkbox":
            old_val = prop.get("checkbox")
        else:
            old_val = None

        if only_empty and _should_skip_for_only_empty(notion_field, old_val):
            continue

        ok, reason = should_update(notion_field, old_val, new_val, conf, old_rate_conf)
        if not ok:
            continue
        if old_val == new_val:
            continue
        changes.append({
            "field": notion_field,
            "old": old_val,
            "new": new_val,
            "reason": reason,
        })
    return changes


def _patch_page(token: str, page_id: str, changes: list[dict]) -> bool:
    properties: dict[str, Any] = {}
    for ch in changes:
        field = ch["field"]
        val = ch["new"]
        if field in ("rate_type", "remote_type", "extraction_method", "pipeline_version"):
            properties[field] = {"select": {"name": str(val)}} if val else {"select": None}
        elif field == "単価（万円）":
            if val is not None:
                val = validate_rate_man(float(val))
            properties[field] = {"number": val}
        elif field == "extraction_confidence":
            properties[field] = {"number": val}
        elif field == "needs_review":
            properties[field] = {"checkbox": bool(val)}
        elif field == "勤務地":
            properties[field] = {"rich_text": [{"text": {"content": str(val)[:2000]}}]} if val else {"rich_text": []}

    resp = requests.patch(
        f"{NOTION_BASE}pages/{page_id}",
        headers=_headers(token),
        json={"properties": properties},
        timeout=30,
    )
    if resp.status_code >= 400:
        logger.warning("PATCH failed %s: %s", page_id, resp.text[:200])
        return False
    return True


def run(
    *,
    dry_run: bool = True,
    limit: int | None = None,
    batch_id: str = "dry_run",
    only_empty: bool = True,
    fields: str = "rate,remote,location",
    page_ids: list[str] | None = None,
    status_filter: str | None = None,
) -> dict[str, Any]:
    token = _load_token()
    field_set = {f.strip() for f in fields.split(",") if f.strip()}
    pages = _query_pages(token, page_ids=page_ids, limit=limit, status_filter=status_filter)

    log_entries: list[dict] = []
    stats = {
        "batch_id": batch_id,
        "dry_run": dry_run,
        "processed": 0,
        "changed": 0,
        "errors": 0,
        "needs_review": 0,
        "non_empty_overwrites": 0,
    }

    for page in pages:
        stats["processed"] += 1
        page_id = page.get("id", "")
        props = page.get("properties", {})
        text = _rt(props.get("案件詳細")) or _rt(props.get("案件情報原文"))
        if not text:
            continue

        extracted = _extract_fields(text, field_set)
        if extracted.get("needs_review"):
            stats["needs_review"] += 1

        changes = _build_changes(props, extracted, only_empty=only_empty)
        if not changes:
            continue

        for ch in changes:
            if ch["reason"] not in ALLOWED_OVERWRITE_REASONS:
                if ch["old"] not in (None, "", 0):
                    stats["non_empty_overwrites"] += 1

        entry = {
            "page_id": page_id,
            "batch_id": batch_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": _title(props.get("案件名"))[:80],
            "changes": changes,
        }
        log_entries.append(entry)
        stats["changed"] += 1

        action = "DRY-RUN" if dry_run else "PATCH"
        logger.info("[%s] %s: %d fields", action, entry["title"], len(changes))

        if not dry_run:
            ok = _patch_page(token, page_id, changes)
            if not ok:
                stats["errors"] += 1
            time.sleep(0.35)

    review_rate = stats["needs_review"] / max(stats["processed"], 1)
    error_rate = stats["errors"] / max(stats["changed"], 1) if stats["changed"] else 0
    if review_rate > 0.05:
        logger.warning("STOP: needs_review rate %.1f%% > 5%%", review_rate * 100)
    if error_rate > 0.02 and not dry_run:
        logger.warning("STOP: error rate %.1f%% > 2%%", error_rate * 100)
    if stats["non_empty_overwrites"] > 0:
        logger.warning("STOP: non-empty overwrites detected: %d", stats["non_empty_overwrites"])

    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"{batch_id}.json"
    log_path.write_text(json.dumps(log_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Log written: %s (%d entries)", log_path, len(log_entries))
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="R5 backfill engine")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-id", default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--only-empty", action="store_true", default=True)
    parser.add_argument("--all-fields", action="store_true", help="Allow non-empty overwrites per policy")
    parser.add_argument("--fields", default="rate,remote,location")
    parser.add_argument("--page-ids", default="", help="Comma-separated page IDs")
    parser.add_argument("--status", default="", help="Filter by matching_status (e.g. ERROR)")
    args = parser.parse_args()

    dry_run = not args.execute
    raw_status = args.status.strip().upper()

    page_ids: list[str] | None
    run_limit: int | None

    if raw_status == "ERROR":
        # ERROR mode: resolve page IDs from SQLite (Notion has no "ERROR" select value)
        error_ids = _fetch_error_case_ids(PROCESSED_DB, limit=args.limit)
        if not error_ids:
            logger.warning("No ERROR cases found in %s", PROCESSED_DB)
            print(json.dumps({"batch_id": args.batch_id, "processed": 0, "changed": 0, "errors": 0, "skipped": "no_error_cases"}, ensure_ascii=False, indent=2))
            return
        logger.info("ERROR mode: %d case IDs from SQLite", len(error_ids))
        page_ids = error_ids
        run_limit = None  # limit already applied in _fetch_error_case_ids
        status_filter = None
    else:
        page_ids = [p.strip() for p in args.page_ids.split(",") if p.strip()] or None
        run_limit = args.limit
        status_filter = raw_status or None

    stats = run(
        dry_run=dry_run,
        limit=run_limit,
        batch_id=args.batch_id,
        only_empty=not args.all_fields,
        fields=args.fields,
        page_ids=page_ids,
        status_filter=status_filter,
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
