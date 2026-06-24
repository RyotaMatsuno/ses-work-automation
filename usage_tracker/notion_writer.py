"""
notion_writer.py - コスト管理DBの作成とレコード書き込み
"""

from __future__ import annotations

from pathlib import Path

import requests
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "config" / ".env"
_env = dotenv_values(ENV_PATH)

NOTION_TOKEN = _env.get("NOTION_API_KEY") or _env.get("NOTION_TOKEN") or ""
PARENT_PAGE_ID = "353450ff-37c0-8145-9e3e-d80c8c8ed594"
DB_ID_FILE = Path(__file__).resolve().parent / "notion_db_id.txt"
DB_NAME = "コスト管理DB"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def _get_or_create_db() -> str:
    if DB_ID_FILE.exists():
        db_id = DB_ID_FILE.read_text().strip()
        if db_id:
            return db_id

    print(f"[notion_writer] Creating DB '{DB_NAME}'...", flush=True)
    payload = {
        "parent": {"type": "page_id", "page_id": PARENT_PAGE_ID},
        "title": [{"type": "text", "text": {"content": DB_NAME}}],
        "properties": {
            "日付": {"date": {}},
            "スクリプト": {"select": {}},
            "モデル": {"select": {}},
            "入力トークン": {"number": {"format": "number"}},
            "出力トークン": {"number": {"format": "number"}},
            "コスト(USD)": {"number": {"format": "number"}},
            "コスト(円)": {"number": {"format": "number"}},
            "月次累計(円)": {"number": {"format": "number"}},
            "名前": {"title": {}},
        },
    }
    resp = requests.post("https://api.notion.com/v1/databases", headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    db_id = resp.json()["id"]
    DB_ID_FILE.write_text(db_id)
    print(f"[notion_writer] DB created: {db_id}", flush=True)
    return db_id


def write_cost_record(
    date_str: str,
    script_name: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    cost_jpy: float,
    monthly_total_jpy: float,
) -> None:
    try:
        db_id = _get_or_create_db()
        title = f"{date_str} {script_name} {model}"
        payload = {
            "parent": {"database_id": db_id},
            "properties": {
                "名前": {"title": [{"text": {"content": title}}]},
                "日付": {"date": {"start": date_str}},
                "スクリプト": {"select": {"name": script_name}},
                "モデル": {"select": {"name": model}},
                "入力トークン": {"number": input_tokens},
                "出力トークン": {"number": output_tokens},
                "コスト(USD)": {"number": round(cost_usd, 6)},
                "コスト(円)": {"number": round(cost_jpy, 2)},
                "月次累計(円)": {"number": round(monthly_total_jpy, 2)},
            },
        }
        resp = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload, timeout=30)
        resp.raise_for_status()
        print(f"[notion_writer] Written: {title}", flush=True)
    except Exception as e:
        print(f"[notion_writer] ERROR: {e}", flush=True)
