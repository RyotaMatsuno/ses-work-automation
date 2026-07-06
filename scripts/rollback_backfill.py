# -*- coding: utf-8 -*-
"""Rollback a backfill batch using backfill_logs/BATCH_ID.json."""

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

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES_WORK = Path(__file__).resolve().parents[1]
LOG_DIR = SES_WORK / "backfill_logs"
NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1/"

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


def _build_rollback_properties(changes: list[dict]) -> dict:
    properties: dict = {}
    for ch in changes:
        field = ch["field"]
        old = ch["old"]
        if field in ("rate_type", "remote_type", "extraction_method", "pipeline_version"):
            properties[field] = {"select": {"name": str(old)}} if old else {"select": None}
        elif field == "単価（万円）":
            properties[field] = {"number": old}
        elif field == "extraction_confidence":
            properties[field] = {"number": old}
        elif field == "needs_review":
            properties[field] = {"checkbox": bool(old) if old is not None else False}
        elif field == "勤務地":
            if old:
                properties[field] = {"rich_text": [{"text": {"content": str(old)[:2000]}}]}
            else:
                properties[field] = {"rich_text": []}
    return properties


def rollback(batch_id: str, page_id: str | None = None, *, dry_run: bool = False) -> dict:
    log_path = LOG_DIR / f"{batch_id}.json"
    if not log_path.exists():
        raise SystemExit(f"Log not found: {log_path}")

    entries = json.loads(log_path.read_text(encoding="utf-8"))
    if page_id:
        entries = [e for e in entries if e.get("page_id") == page_id]
    if not entries:
        raise SystemExit("No matching entries to rollback")

    token = _load_token()
    stats = {"rolled_back": 0, "errors": 0, "dry_run": dry_run}

    for entry in entries:
        pid = entry["page_id"]
        props = _build_rollback_properties(entry.get("changes", []))
        if dry_run:
            logger.info("[DRY-RUN ROLLBACK] %s: %d fields", pid[:8], len(props))
            stats["rolled_back"] += 1
            continue
        resp = requests.patch(
            f"{NOTION_BASE}pages/{pid}",
            headers=_headers(token),
            json={"properties": props},
            timeout=30,
        )
        if resp.status_code >= 400:
            logger.warning("Rollback failed %s: %s", pid, resp.text[:200])
            stats["errors"] += 1
        else:
            stats["rolled_back"] += 1
        time.sleep(0.35)

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Rollback backfill batch")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--page-id", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    stats = rollback(args.batch_id, args.page_id or None, dry_run=args.dry_run)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
