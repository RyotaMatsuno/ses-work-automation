# -*- coding: utf-8 -*-
"""Replay pilot 19 cases with fixed extractors and verify bug fixes + regression."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES_WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SES_WORK))

from extractors.rate_extractor import extract_rate
from extractors.remote_extractor import extract_remote

PILOT_LOG = SES_WORK / "backfill_logs" / "pilot_001.json"
DIFF_OUT = SES_WORK / "research_results" / "pilot_replay_diff_20260625.md"
NOTION_BASE = "https://api.notion.com/v1/"
NOTION_VERSION = "2022-06-28"

# Rolled back during pilot rollback test
SKIP_PAGE = "38a450ff-37c0-8191-9ec0-fd4111022d25"

BUG_RATE_UNIT = "38a450ff-37c0-8194-a98c-d0fe9fbe9993"  # 生命保険 単価55万
BUG_SKILL_ORDER = "38a450ff-37c0-816f-aa35-cbd3f6f81875"  # 大規模金融 70万（スキル見合い）
BUG_REMOTE_INITIAL = "38a450ff-37c0-81e8-a603-dedd8d024ec4"  # Java/Oracle 初日出社
MINOR_APPROX = "38a450ff-37c0-81fc-a077-f3844f73d504"  # ServiceNow 50万円前後

FIX_PAGES = {BUG_RATE_UNIT, BUG_SKILL_ORDER, BUG_REMOTE_INITIAL, MINOR_APPROX}


def _load_token() -> str:
    env_path = SES_WORK / "config" / ".env"
    env = dict(dotenv_values(env_path, encoding="utf-8"))
    env.update({k: v for k, v in os.environ.items() if v})
    return env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN") or ""


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _fetch_page(token: str, page_id: str) -> dict:
    resp = requests.get(f"{NOTION_BASE}pages/{page_id}", headers=_headers(token), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _rt(prop: dict | None) -> str:
    if not prop or prop.get("type") != "rich_text":
        return ""
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


def _snapshot_from_log(entry: dict) -> dict:
    snap = {"rate_type": None, "remote_type": None, "rate_man": None}
    for ch in entry.get("changes", []):
        if ch["field"] == "rate_type":
            snap["rate_type"] = ch["new"]
        elif ch["field"] == "remote_type":
            snap["remote_type"] = ch["new"]
        elif ch["field"] == "単価（万円）":
            snap["rate_man"] = ch["new"]
    return snap


def _extract_snapshot(text: str) -> dict:
    rate = extract_rate(text)
    remote = extract_remote(text)
    return {
        "rate_type": rate.rate_type,
        "rate_max_man": rate.rate_max_man,
        "remote_type": remote.remote_type,
        "initial_onsite": remote.initial_onsite,
        "initial_onsite_required": remote.initial_onsite_required,
    }


def _check_bug_fixes(page_id: str, new: dict, text: str) -> list[str]:
    errors: list[str] = []
    if page_id == BUG_RATE_UNIT:
        if new["rate_max_man"] != 55:
            errors.append(f"bug1: expected rate_max=55, got {new['rate_max_man']}")
        if new["rate_max_man"] == 550000:
            errors.append("bug1: rate still in yen units (550000)")
    if page_id == BUG_SKILL_ORDER:
        if new["rate_type"] != "skill_dependent_with_cap":
            errors.append(f"bug2: expected skill_dependent_with_cap, got {new['rate_type']}")
        if new["rate_max_man"] != 70:
            errors.append(f"bug2: expected rate_max=70, got {new['rate_max_man']}")
    if page_id == BUG_REMOTE_INITIAL:
        if new["remote_type"] != "full_remote":
            errors.append(f"bug3: expected full_remote, got {new['remote_type']}")
        if not new.get("initial_onsite_required"):
            errors.append("bug3: expected initial_onsite_required=True")
    if page_id == MINOR_APPROX:
        if new["rate_type"] != "fixed_upper_only":
            errors.append(f"minor: expected fixed_upper_only, got {new['rate_type']}")
        if new["rate_max_man"] != 50:
            errors.append(f"minor: expected rate_max=50, got {new['rate_max_man']}")
    return errors


def run() -> int:
    if not PILOT_LOG.exists():
        print(f"Missing {PILOT_LOG}")
        return 1

    token = _load_token()
    if not token:
        print("NOTION_API_KEY not set")
        return 1

    entries = json.loads(PILOT_LOG.read_text(encoding="utf-8"))
    errors: list[str] = []
    diffs: list[str] = ["# Pilot Replay Diff\n"]
    normal_unchanged = 0
    normal_total = 0

    for entry in entries:
        page_id = entry["page_id"]
        if page_id == SKIP_PAGE:
            continue

        page = _fetch_page(token, page_id)
        props = page.get("properties", {})
        text = _rt(props.get("案件詳細")) or _rt(props.get("案件情報原文"))
        old = _snapshot_from_log(entry)
        new = _extract_snapshot(text)

        diffs.append(f"\n## {entry['title']}\n")
        diffs.append(f"- page_id: `{page_id}`\n")
        diffs.append(f"- before: rate_type={old['rate_type']}, remote={old['remote_type']}, rate_man={old['rate_man']}\n")
        diffs.append(f"- after:  rate_type={new['rate_type']}, remote={new['remote_type']}, rate_max={new['rate_max_man']}, initial_onsite={new['initial_onsite_required']}\n")

        if page_id in FIX_PAGES:
            errors.extend(_check_bug_fixes(page_id, new, text))
        else:
            normal_total += 1
            if old["rate_type"] == new["rate_type"] and old["remote_type"] == new["remote_type"]:
                normal_unchanged += 1
            else:
                errors.append(
                    f"regression {entry['title'][:30]}: "
                    f"rate {old['rate_type']}->{new['rate_type']}, "
                    f"remote {old['remote_type']}->{new['remote_type']}"
                )

        time.sleep(0.2)

    DIFF_OUT.parent.mkdir(exist_ok=True)
    DIFF_OUT.write_text("".join(diffs), encoding="utf-8")
    print(f"Replay: {normal_unchanged}/{normal_total} normal cases unchanged")
    print(f"Diff written: {DIFF_OUT}")

    if errors:
        print(f"FAILURES ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("PASS: all replay checks OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
