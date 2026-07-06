# -*- coding: utf-8 -*-
"""Verify Notion case DB schema including R5 properties."""

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

REQUIRED_LEGACY = {
    "案件名": "title",
    "必要スキル": "multi_select",
    "尚可スキル": "multi_select",
    "単価（万円）": "number",
    "勤務地": "rich_text",
    "案件詳細": "rich_text",
    "ステータス": "select",
}

REQUIRED_R5 = {
    "rate_type": ("select", {
        "fixed_range", "fixed_upper_only", "skill_dependent_with_cap",
        "skill_dependent_no_number", "not_present", "unknown",
    }),
    "remote_type": ("select", {
        "full_remote", "hybrid", "onsite", "remote_possible", "unknown",
    }),
    "extraction_method": ("select", {"regex", "llm", "manual", "legacy"}),
    "extraction_confidence": ("number", set()),
    "pipeline_version": ("select", {"v1", "v2"}),
    "needs_review": ("checkbox", set()),
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


def verify() -> list[str]:
    token = _load_token()
    resp = requests.get(
        f"{NOTION_BASE}databases/{CASE_DB_ID}",
        headers=_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    props = resp.json().get("properties", {})
    errors: list[str] = []

    for name, expected_type in REQUIRED_LEGACY.items():
        if name not in props:
            errors.append(f"Missing legacy property: {name}")
            continue
        if props[name].get("type") != expected_type:
            errors.append(
                f"Legacy type mismatch {name}: expected {expected_type}, got {props[name].get('type')}"
            )

    for name, (expected_type, options) in REQUIRED_R5.items():
        if name not in props:
            errors.append(f"Missing R5 property: {name}")
            continue
        if props[name].get("type") != expected_type:
            errors.append(
                f"R5 type mismatch {name}: expected {expected_type}, got {props[name].get('type')}"
            )
            continue
        if options and expected_type == "select":
            actual = {o.get("name") for o in props[name].get("select", {}).get("options", [])}
            missing = options - actual
            if missing:
                errors.append(f"R5 select options missing for {name}: {sorted(missing)}")

    return errors


def main() -> None:
    errors = verify()
    if errors:
        for err in errors:
            print(f"❌ {err}")
        raise SystemExit(1)
    print("✅ verify_notion_schema: PASS (legacy + R5 properties OK)")


if __name__ == "__main__":
    main()
