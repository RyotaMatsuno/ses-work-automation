"""Rollback runner — reverts the latest apply using pre_update_snapshot.json."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
import requests

_ENV_PATH = Path(__file__).parent.parent / "config" / ".env"
load_dotenv(_ENV_PATH)

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_VERSION = "2022-06-28"
_RATE_LIMIT_SLEEP = 0.35
_OUTPUT_DIR = Path(__file__).parent / "output"


def _notion_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _build_restore_payload(decisions: list[dict]) -> dict:
    props: dict = {}
    for d in decisions:
        if d["action"] != "update":
            continue
        field = d["field"]
        old_val = d["old"]

        if field == "スキル":
            items = old_val if isinstance(old_val, list) else []
            props[field] = {"multi_select": [{"name": s} for s in items]}
        elif field == "単価（万円）":
            props[field] = {"number": old_val}
        elif field == "最寄り駅":
            content = old_val or ""
            props[field] = {"rich_text": [{"text": {"content": str(content)}}] if content else []}
        elif field == "経験年数":
            props[field] = {"number": old_val}
        elif field == "稼働可能日":
            props[field] = {"date": {"start": str(old_val)} if old_val else None}
        elif field == "居住地":
            props[field] = {"select": {"name": str(old_val)} if old_val else None}

    return props


def main() -> None:
    parser = argparse.ArgumentParser(description="Rollback the latest apply")
    parser.add_argument("--latest", action="store_true", required=True, help="Rollback latest apply")
    parser.add_argument("--snapshot", type=str, default=None, help="Path to snapshot file (optional)")
    args = parser.parse_args()

    snapshot_path = Path(args.snapshot) if args.snapshot else _OUTPUT_DIR / "pre_update_snapshot.json"
    if not snapshot_path.exists():
        print(f"Snapshot not found: {snapshot_path}", file=sys.stderr)
        sys.exit(1)

    with snapshot_path.open(encoding="utf-8") as f:
        snapshot = json.load(f)

    records = snapshot.get("records", [])
    restored = 0
    errors = 0

    for r in records:
        updates = [d for d in r.get("decisions", []) if d["action"] == "update"]
        if not updates:
            continue

        payload = _build_restore_payload(updates)
        if not payload:
            continue

        page_id = r["id"]
        try:
            url = f"https://api.notion.com/v1/pages/{page_id}"
            resp = requests.patch(url, headers=_notion_headers(), json={"properties": payload}, timeout=30)
            resp.raise_for_status()
            print(f"  Restored: {r.get('name', page_id[:8])}")
            restored += 1
            time.sleep(_RATE_LIMIT_SLEEP)
        except Exception as e:
            print(f"  ERROR restoring {r.get('name', page_id[:8])}: {e}", file=sys.stderr)
            errors += 1

    print(f"\nRollback complete. Restored: {restored}, Errors: {errors}")


if __name__ == "__main__":
    main()
