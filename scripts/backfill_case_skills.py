#!/usr/bin/env python3
"""Task AY: 必須スキル空の既存案件をルールベースでバックフィル（LLM不使用）。"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

SES_WORK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SES_WORK))

from mail_pipeline.project_notion_save import (
    BACKFILL_SOURCE_TAG,
    backfill_note_append,
    extract_skills_for_backfill,
)

RATE_LIMIT_SEC = 0.35
MAX_PER_RUN = 200
PROP_REQ_SKILLS = "必要スキル"
PROP_OPT_SKILLS = "尚可スキル"
LOG_PATH = SES_WORK / "mail_pipeline" / "logs" / "backfill_case_skills.jsonl"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

NOTION_HEADERS: dict[str, str] = {}
PROJECT_DB = ""


def load_env() -> None:
    global NOTION_HEADERS, PROJECT_DB
    env_path = SES_WORK / "config" / ".env"
    for key, val in dotenv_values(env_path).items():
        if val and key not in os.environ:
            os.environ[key] = val
    token = os.environ.get("NOTION_API_KEY", "")
    PROJECT_DB = os.environ.get("NOTION_PROJECT_DB_ID", "")
    NOTION_HEADERS = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }


def get_database_property_names(database_id: str) -> set[str]:
    if not database_id or not NOTION_HEADERS.get("Authorization"):
        return set()
    resp = requests.get(
        f"https://api.notion.com/v1/databases/{database_id}",
        headers=NOTION_HEADERS,
        timeout=30,
    )
    if resp.status_code != 200:
        return set()
    return set(resp.json().get("properties", {}).keys())


def _rich_text(props: dict, name: str) -> str:
    items = props.get(name, {}).get("rich_text", [])
    return "".join(i.get("plain_text", "") for i in items).strip()


def _multi_select(props: dict, name: str) -> list[str]:
    return [o.get("name", "") for o in props.get(name, {}).get("multi_select", []) if o.get("name")]


def _title(props: dict, name: str = "案件名") -> str:
    items = props.get(name, {}).get("title", [])
    return "".join(i.get("plain_text", "") for i in items).strip()


def query_empty_skill_cases(limit: int) -> list[dict]:
    payload = {
        "page_size": min(limit, 100),
        "filter": {"property": PROP_REQ_SKILLS, "multi_select": {"is_empty": True}},
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


def build_patch(props: dict, req: list[str], opt: list[str], prop_names: set[str]) -> dict:
    patch: dict = {}
    current_req = _multi_select(props, PROP_REQ_SKILLS)
    current_opt = _multi_select(props, PROP_OPT_SKILLS)
    if not current_req and req:
        patch[PROP_REQ_SKILLS] = {"multi_select": [{"name": s} for s in req]}
    if not current_opt and opt:
        patch[PROP_OPT_SKILLS] = {"multi_select": [{"name": s} for s in opt]}
    if "備考" in prop_names:
        existing = _rich_text(props, "備考")
        patch["備考"] = {
            "rich_text": [{"text": {"content": backfill_note_append(existing)[:2000]}}]
        }
    return patch


def run_backfill(*, dry_run: bool = True, limit: int = MAX_PER_RUN) -> dict:
    if not PROJECT_DB:
        raise RuntimeError("NOTION_PROJECT_DB_ID is not set")

    prop_names = set(get_database_property_names(PROJECT_DB))
    pages = query_empty_skill_cases(limit)
    stats = {
        "candidates": len(pages),
        "patched": 0,
        "skipped_no_skills": 0,
        "errors": 0,
        "dry_run": dry_run,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    for page in pages:
        page_id = page["id"]
        props = page.get("properties", {})
        title = _title(props)
        detail = _rich_text(props, "案件詳細")
        raw = _rich_text(props, "案件情報原文")
        req, opt = extract_skills_for_backfill(title, detail, raw)
        if not req and not opt:
            stats["skipped_no_skills"] += 1
            log.info("SKIP no skills extracted: %s", title[:50])
            continue

        patch = build_patch(props, req, opt, prop_names)
        if not patch.get(PROP_REQ_SKILLS) and not patch.get(PROP_OPT_SKILLS):
            stats["skipped_no_skills"] += 1
            continue

        log.info(
            "PATCH %s | req=%s opt=%s tag=%s%s",
            title[:40],
            req,
            opt,
            BACKFILL_SOURCE_TAG in patch.get("備考", {}).get("rich_text", [{}])[0].get("text", {}).get("content", ""),
            " [DRY_RUN]" if dry_run else "",
        )

        entry = {
            "page_id": page_id,
            "title": title,
            "required_skills": req,
            "optional_skills": opt,
            "dry_run": dry_run,
        }
        with LOG_PATH.open("a", encoding="utf-8") as log_f:
            log_f.write(json.dumps(entry, ensure_ascii=False) + "\n")

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
    parser = argparse.ArgumentParser(description="Backfill empty 必要スキル on Notion project DB")
    parser.add_argument("--dry-run", action="store_true", help="Preview only (default)")
    parser.add_argument("--execute", action="store_true", help="Write to Notion")
    parser.add_argument("--limit", type=int, default=MAX_PER_RUN)
    args = parser.parse_args()
    dry_run = not args.execute
    if args.execute:
        log.warning("LIVE MODE: writing to Notion")
    stats = run_backfill(dry_run=dry_run, limit=min(args.limit, MAX_PER_RUN))
    log.info("Done: %s", stats)
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
