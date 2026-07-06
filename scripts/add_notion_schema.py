# -*- coding: utf-8 -*-
"""Add R5 schema properties to Notion case database (idempotent)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES_WORK = Path(__file__).resolve().parents[1]
ENV_PATH = SES_WORK / "config" / ".env"
CASE_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1/"

NEW_PROPERTIES: dict[str, dict] = {
    "rate_type": {
        "select": {
            "options": [
                {"name": "fixed_range", "color": "blue"},
                {"name": "fixed_upper_only", "color": "green"},
                {"name": "skill_dependent_with_cap", "color": "yellow"},
                {"name": "skill_dependent_no_number", "color": "orange"},
                {"name": "not_present", "color": "gray"},
                {"name": "unknown", "color": "red"},
            ]
        }
    },
    "remote_type": {
        "select": {
            "options": [
                {"name": "full_remote", "color": "blue"},
                {"name": "hybrid", "color": "green"},
                {"name": "onsite", "color": "yellow"},
                {"name": "remote_possible", "color": "orange"},
                {"name": "unknown", "color": "gray"},
            ]
        }
    },
    "extraction_method": {
        "select": {
            "options": [
                {"name": "regex", "color": "blue"},
                {"name": "llm", "color": "purple"},
                {"name": "manual", "color": "green"},
                {"name": "legacy", "color": "gray"},
            ]
        }
    },
    "extraction_confidence": {"number": {"format": "number"}},
    "pipeline_version": {
        "select": {
            "options": [
                {"name": "v1", "color": "gray"},
                {"name": "v2", "color": "blue"},
            ]
        }
    },
    "needs_review": {"checkbox": {}},
}


def _load_token() -> str:
    env = dict(dotenv_values(ENV_PATH, encoding="utf-8"))
    env.update({k: v for k, v in os.environ.items() if v})
    token = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN", "")
    if not token:
        print(f"[ERROR] NOTION_API_KEY not set ({ENV_PATH})")
        raise SystemExit(1)
    return token


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def main() -> None:
    token = _load_token()
    headers = _headers(token)

    resp = requests.get(f"{NOTION_BASE}databases/{CASE_DB_ID}", headers=headers, timeout=30)
    resp.raise_for_status()
    existing = resp.json().get("properties", {})

    to_add = {name: spec for name, spec in NEW_PROPERTIES.items() if name not in existing}
    if not to_add:
        print("✅ All 6 R5 properties already exist — skipped")
        return

    patch = requests.patch(
        f"{NOTION_BASE}databases/{CASE_DB_ID}",
        headers=headers,
        json={"properties": to_add},
        timeout=30,
    )
    if patch.status_code != 200:
        print(f"❌ PATCH failed: {patch.status_code} {patch.text[:500]}")
        raise SystemExit(1)

    added = ", ".join(to_add.keys())
    print(f"✅ Added properties: {added}")


if __name__ == "__main__":
    main()
