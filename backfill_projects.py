#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task S: Backfill empty skills/price on Notion project DB from raw_inbox.db (rule-only)."""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

SES_WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(SES_WORK))

from mail_pipeline.mail_pipeline import NOTION_HEADERS, PROJECT_DB, VALID_SKILLS
from mail_pipeline.price_extractor import extract_price, resolve_final_price
from mail_pipeline.skill_extractor import merge_extracted_skills

RAW_INBOX_DB = SES_WORK / "mail_pipeline" / "raw_inbox.db"
RATE_LIMIT_SEC = 0.3
MAX_PER_RUN = 100
PROP_STATUS = "ステータス"
PROP_REQ_SKILLS = "必要スキル"
PROP_OPT_SKILLS = "尚可スキル"
PROP_PRICE = "単価（万円）"
PROP_MSG_ID = "元MessageID"
STATUS_RECRUITING = "募集中"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def load_env() -> None:
    env_path = SES_WORK / "config" / ".env"
    for key, val in dotenv_values(env_path).items():
        if val and key not in os.environ:
            os.environ[key] = val


def _rich_text(props: dict, name: str) -> str:
    items = props.get(name, {}).get("rich_text", [])
    return "".join(i.get("plain_text", "") for i in items).strip()


def _multi_select(props: dict, name: str) -> list[str]:
    return [o.get("name", "") for o in props.get(name, {}).get("multi_select", []) if o.get("name")]


def _number(props: dict, name: str) -> float | None:
    val = props.get(name, {}).get("number")
    return float(val) if val is not None else None


def _title(props: dict, name: str = "案件名") -> str:
    items = props.get(name, {}).get("title", [])
    return "".join(i.get("plain_text", "") for i in items).strip()


def query_backfill_candidates(limit: int) -> list[dict]:
    """募集中かつ skills空 or price空 のレコードを取得。"""
    payload = {
        "page_size": min(limit, 100),
        "filter": {
            "and": [
                {"property": PROP_STATUS, "select": {"equals": STATUS_RECRUITING}},
                {
                    "or": [
                        {"property": PROP_REQ_SKILLS, "multi_select": {"is_empty": True}},
                        {"property": PROP_PRICE, "number": {"is_empty": True}},
                    ]
                },
            ]
        },
    }
    results: list[dict] = []
    while len(results) < limit:
        resp = requests.post(
            f"https://api.notion.com/v1/databases/{PROJECT_DB}/query",
            headers=NOTION_HEADERS,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))
        if not data.get("has_more") or len(results) >= limit:
            break
        payload["start_cursor"] = data["next_cursor"]
        time.sleep(RATE_LIMIT_SEC)
    return results[:limit]


def lookup_email(message_id: str) -> tuple[str, str] | None:
    if not message_id or not RAW_INBOX_DB.exists():
        return None
    conn = sqlite3.connect(RAW_INBOX_DB)
    try:
        row = conn.execute(
            "SELECT subject, body_text FROM raw_emails WHERE message_id = ? LIMIT 1",
            (message_id,),
        ).fetchone()
        if row:
            return (row[0] or "", row[1] or "")
    finally:
        conn.close()
    return None


def extract_from_page(page: dict) -> dict:
    props = page.get("properties", {})
    msg_id = _rich_text(props, PROP_MSG_ID)
    subject, body = "", ""
    email = lookup_email(msg_id)
    if email:
        subject, body = email
    if not body:
        body = _rich_text(props, "案件詳細") or _rich_text(props, "案件情報原文")
    if not subject:
        subject = _title(props)

    price_result = extract_price(subject, body)
    final_price = resolve_final_price(None, subject, body)
    if price_result.get("confidence") == "suspicious":
        final_price = None

    req, opt = merge_extracted_skills([], [], subject, body, VALID_SKILLS)
    return {
        "msg_id": msg_id,
        "subject": subject[:60],
        "price": final_price,
        "price_confidence": price_result.get("confidence"),
        "required_skills": req,
        "optional_skills": opt,
    }


def build_patch(props: dict, extracted: dict) -> dict:
    """空欄のみ埋める PATCH ペイロードを構築。"""
    patch: dict = {}
    current_req = _multi_select(props, PROP_REQ_SKILLS)
    current_opt = _multi_select(props, PROP_OPT_SKILLS)
    current_price = _number(props, PROP_PRICE)

    if not current_req and extracted["required_skills"]:
        patch[PROP_REQ_SKILLS] = {
            "multi_select": [{"name": s} for s in extracted["required_skills"]]
        }
    if not current_opt and extracted["optional_skills"]:
        patch[PROP_OPT_SKILLS] = {
            "multi_select": [{"name": s} for s in extracted["optional_skills"]]
        }
    if current_price is None and extracted["price"] is not None:
        patch[PROP_PRICE] = {"number": extracted["price"]}
    return patch


def backfill(dry_run: bool = True, limit: int = MAX_PER_RUN) -> dict:
    if not PROJECT_DB:
        raise RuntimeError("NOTION_PROJECT_DB_ID is not set")

    pages = query_backfill_candidates(limit)
    stats = {
        "candidates": len(pages),
        "patched": 0,
        "skipped_no_patch": 0,
        "skipped_no_source": 0,
        "errors": 0,
        "dry_run": dry_run,
    }

    for page in pages:
        page_id = page["id"]
        props = page.get("properties", {})
        title = _title(props)
        extracted = extract_from_page(page)

        if not extracted["msg_id"] and not extracted["required_skills"] and extracted["price"] is None:
            if not _rich_text(props, "案件詳細"):
                stats["skipped_no_source"] += 1
                log.info("SKIP no source: %s", title[:40])
                continue

        patch = build_patch(props, extracted)
        if not patch:
            stats["skipped_no_patch"] += 1
            log.info("SKIP nothing to fill: %s", title[:40])
            continue

        log.info(
            "PATCH %s | price=%s skills=%s opt=%s%s",
            title[:40],
            patch.get(PROP_PRICE, {}).get("number"),
            [s["name"] for s in patch.get(PROP_REQ_SKILLS, {}).get("multi_select", [])],
            [s["name"] for s in patch.get(PROP_OPT_SKILLS, {}).get("multi_select", [])],
            " [DRY_RUN]" if dry_run else "",
        )

        if dry_run:
            stats["patched"] += 1
            continue

        resp = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=NOTION_HEADERS,
            json={"properties": patch},
            timeout=30,
        )
        time.sleep(RATE_LIMIT_SEC)
        if resp.status_code == 200:
            stats["patched"] += 1
        else:
            stats["errors"] += 1
            log.error("ERROR %s: %s %s", page_id, resp.status_code, resp.text[:200])

    return stats


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(description="Backfill Notion project skills/price from raw_inbox")
    parser.add_argument("--limit", type=int, default=MAX_PER_RUN, help="Max records per run")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Write to Notion (default: DRY_RUN unless DRY_RUN=0 in env)",
    )
    args = parser.parse_args()

    dry_run = os.environ.get("DRY_RUN", "1") != "0" and not args.execute
    if not dry_run:
        log.warning("LIVE MODE: writing to Notion")

    stats = backfill(dry_run=dry_run, limit=min(args.limit, MAX_PER_RUN))
    log.info("Done: %s", stats)
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
