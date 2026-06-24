#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Notion AI作業キュー登録 + SES Wiki修正"""

import os
import sys
from datetime import datetime

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv("C:/Users/ma_py/OneDrive/デスクトップ/ses_work/config/.env")

NOTION_TOKEN = os.environ["NOTION_API_KEY"]
WIKI_BLOCK_ID = "353450ff-37c0-8145-9e3e-d80c8c8ed594"
AI_QUEUE_DB_ID = "37a450ff-37c0-819a-981b-c2e06ed282bb"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# === 1. AI作業キューDBにタスク登録 ===
now_iso = datetime.now().isoformat()
task_id = f"anthropic_admin_key_automation_{datetime.now().strftime('%Y%m%d')}"

queue_payload = {
    "parent": {"database_id": AI_QUEUE_DB_ID},
    "properties": {
        "task_id": {"title": [{"text": {"content": task_id}}]},
        "種別": {"select": {"name": "開発"}},
        "優先度": {"select": {"name": "Mid"}},
        "担当": {"select": {"name": "jobz"}},
        "状態": {"select": {"name": "queued"}},
        "受付元": {"select": {"name": "ジョブズ提案"}},
        "作成日時": {"date": {"start": now_iso}},
        "入力データ": {
            "rich_text": [
                {
                    "text": {
                        "content": "Anthropic Admin Key を console で作成し、usage を自動取得して LINE 通知する仕組みを構築。"
                        "CostGuard と並ぶ二重監視。"
                        "手順: (1) 松野が console.anthropic.com → Settings → API Keys → Create Admin Key を実施。"
                        "(2) ジョブズが Anthropic Admin API (v1/organizations/usage_report/messages, v1/organizations/cost_report) で日次使用量を取得するスクリプト作成。"
                        "(3) common/ledger.py と統合し、Cursor Pro / OpenAI / Anthropic 三系統の統合監視に拡張。"
                        "(4) 異常値(1日$10超)で LINE 通知。"
                        "発動契機: 論点B確定の延長で松野から正式タスク化指示(2026-06-16)。"
                    }
                }
            ]
        },
        "コスト見込み": {"number": 1.0},  # 開発時にかかるAPIコスト見込み $1程度
        "使用許可": {"select": {"name": "OK"}},
    },
}

resp = requests.post(
    "https://api.notion.com/v1/pages",
    headers=headers,
    json=queue_payload,
    timeout=30,
)

if resp.status_code == 200:
    print("OK AI作業キュー登録成功")
    print(f"   task_id: {task_id}")
    print(f"   page_id: {resp.json().get('id')}")
else:
    print(f"NG AI作業キュー登録失敗: {resp.status_code}")
    print(resp.text[:1500])
