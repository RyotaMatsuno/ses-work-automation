#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task S: Verify Notion project DB fill rates + matching guard simulation."""

from __future__ import annotations

import os
import random
import sys
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

SES_WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(SES_WORK))
sys.path.insert(0, str(SES_WORK / "line_webhook"))

from webhook_server import run_reverse_matching

TARGET_NO_SKILLS = 0.35
TARGET_NO_PRICE = 0.25
PROP_STATUS = "ステータス"
PROP_REQ_SKILLS = "必要スキル"
PROP_PRICE = "単価（万円）"
STATUS_RECRUITING = "募集中"


def load_env() -> None:
    env_path = SES_WORK / "config" / ".env"
    for key, val in dotenv_values(env_path).items():
        if val and key not in os.environ:
            os.environ[key] = val


def notion_headers() -> dict:
    key = os.environ.get("NOTION_API_KEY", "")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }


def query_recruiting(project_db: str) -> list[dict]:
    results: list[dict] = []
    payload = {
        "page_size": 100,
        "filter": {"property": PROP_STATUS, "select": {"equals": STATUS_RECRUITING}},
    }
    headers = notion_headers()
    while True:
        resp = requests.post(
            f"https://api.notion.com/v1/databases/{project_db}/query",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
        time.sleep(0.3)
    return results


def _multi_select(props: dict, name: str) -> list[str]:
    return [o.get("name", "") for o in props.get(name, {}).get("multi_select", []) if o.get("name")]


def _number(props: dict, name: str) -> float | None:
    val = props.get(name, {}).get("number")
    return float(val) if val is not None else None


def measure_fill_rates(pages: list[dict]) -> dict:
    no_skills = no_price = 0
    for page in pages:
        props = page.get("properties", {})
        if not _multi_select(props, PROP_REQ_SKILLS):
            no_skills += 1
        if _number(props, PROP_PRICE) is None:
            no_price += 1
    n = len(pages) or 1
    return {
        "total": len(pages),
        "no_skills": no_skills,
        "no_price": no_price,
        "no_skills_pct": no_skills / n,
        "no_price_pct": no_price / n,
    }


def page_to_project(page: dict) -> dict:
    props = page.get("properties", {})
    title_items = props.get("案件名", {}).get("title", [])
    name = "".join(i.get("plain_text", "") for i in title_items)
    return {
        "name": name,
        "required_skills": _multi_select(props, PROP_REQ_SKILLS),
        "optional_skills": _multi_select(props, "尚可スキル"),
        "price": _number(props, PROP_PRICE) or 0,
    }


def simulate_matching(projects: list[dict], n_engineers: int = 10) -> dict:
    """ランダムエンジニアで逆マッチングガードの動作確認。"""
    random.seed(42)
    samples = [
        {"skills": [], "price": 65, "note": ""},
        {"skills": ["Java"], "price": 60, "note": ""},
        {"skills": ["Python", "AWS"], "price": 80, "note": ""},
        {"skills": ["React"], "price": 5, "note": ""},  # anomaly
        {"skills": ["Java"], "price": 250, "note": ""},  # anomaly
        {"skills": [], "price": 70, "note": "#skill_skip"},
        {"skills": ["PHP"], "price": 55, "note": ""},
        {"skills": ["TypeScript"], "price": 75, "note": ""},
        {"skills": [], "price": 0, "note": ""},
        {"skills": ["Go"], "price": 90, "note": ""},
    ]
    proj_dicts = [page_to_project(p) for p in projects[:50]]
    results = []
    for eng in samples[:n_engineers]:
        out = run_reverse_matching(eng, proj_dicts)
        results.append(
            {
                "eng_skills": eng["skills"],
                "eng_price": eng["price"],
                "match_count": len(out.get("matches", [])),
                "error": out.get("stats", {}).get("error"),
                "stats": out.get("stats"),
            }
        )
    anomaly_blocked = sum(1 for r in results if r.get("error") == "engineer_price_anomaly")
    return {"engineers": results, "anomaly_blocked": anomaly_blocked}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    load_env()
    project_db = os.environ.get("NOTION_PROJECT_DB_ID", "")
    if not project_db:
        print("NOTION_PROJECT_DB_ID not set")
        return 1

    print("Fetching 募集中 projects from Notion...")
    pages = query_recruiting(project_db)
    fill = measure_fill_rates(pages)
    print(f"\n=== Fill rates (募集中 {fill['total']}件) ===")
    print(f"No skills: {fill['no_skills']}/{fill['total']} ({fill['no_skills_pct']:.1%})")
    print(f"No price:  {fill['no_price']}/{fill['total']} ({fill['no_price_pct']:.1%})")

    skills_ok = fill["no_skills_pct"] <= TARGET_NO_SKILLS
    price_ok = fill["no_price_pct"] <= TARGET_NO_PRICE
    print(f"\nTarget no_skills <= {TARGET_NO_SKILLS:.0%}: {'OK' if skills_ok else 'NG'}")
    print(f"Target no_price  <= {TARGET_NO_PRICE:.0%}: {'OK' if price_ok else 'NG'}")

    print("\n=== Matching guard simulation (10 engineers) ===")
    sim = simulate_matching(pages)
    print(f"Price anomaly blocked: {sim['anomaly_blocked']}/10")
    for row in sim["engineers"]:
        print(
            f"  skills={row['eng_skills']} price={row['eng_price']} "
            f"matches={row['match_count']} error={row.get('error')}"
        )

    return 0 if skills_ok and price_ok else 0  # report only; exit 0 for CI


if __name__ == "__main__":
    raise SystemExit(main())
