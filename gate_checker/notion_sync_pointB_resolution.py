#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Notion SES Wiki 追記: GPT-5.4 STOP級指摘の3点解消結果"""

import os
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv("C:/Users/ma_py/OneDrive/デスクトップ/ses_work/config/.env")

NOTION_TOKEN = os.environ["NOTION_API_KEY"]
WIKI_BLOCK_ID = "353450ff-37c0-8145-9e3e-d80c8c8ed594"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def heading(text, level=3):
    return {
        "object": "block",
        "type": f"heading_{level}",
        f"heading_{level}": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def para(text):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def bullet(text):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


children = [
    heading("2026-06-16 論点B GPT-5.4 STOP級指摘 → 3点解消", 2),
    para(
        "ジョブズ独断判断禁止ルールに従い、論点B(案A確定)をGPT-5.4で批判的に再検証した結果、STOP級指摘が出た。3点確認を完了させ、案A確定に正式格上げ。"
    ),
    heading("指摘1: Cursor Total 6% と Auto 8% の母数整合"),
    para("解消: 松野UIで▾展開ビュー確認。"),
    bullet("Total = Auto + API の加重合算"),
    bullet("Auto + Composer = 8% (Cursor提供モデル単体)"),
    bullet("API = 0% (Your plan includes at least $20 of API usage)"),
    bullet(
        "重要発見: Cursor Pro $20 は Auto枠 + 最低$20分のAPI使用枠を含む。Anthropic Key ONでAPIを使ってもまずCursor Pro $20枠に吸収される仕様"
    ),
    heading("指摘2: Anthropic 実課金確認"),
    para("解消: Anthropic Console Usage画面を実測確認 (過去14日)"),
    bullet("6/01: 約$68, 6/02: 約$63 (memory既知の $50.88/日インシデント時期)"),
    bullet("6/03: 約$43, 6/04: 約$44 (インシデント余波)"),
    bullet("累計 6/01-6/04 で 約$220のスパイク"),
    bullet("6/05以降: ほぼゼロ (CostGuard効果 + Cursor完全移行 + ChatGPT Plus解約の合わせ技)"),
    bullet("直近7日 (6/10-6/16): $1-2/日 ≒ 月換算 $30-60 程度"),
    bullet("→ Cursor Pro経由のSonnet 4.6使用は Anthropic 直接課金を発生させないことを実測確認"),
    heading("指摘3: 超過時運用明文化"),
    para("解消: ses_work/MODEL_ROUTING.md を作成"),
    bullet("通常運用: Cursor Pro $20 で Sonnet 4.6 / gate_checker系は OpenAI API + CostGuard"),
    bullet("しきい値監視: Cursor 50%/70%/85% でアクション差別化"),
    bullet("Anthropic Console 週次チェックを新規ルール化 (月曜推奨)"),
    bullet("超過時フォールバック手順を明文化 (デフォルト推奨: 翌日待ち)"),
    bullet("Anthropic Key OFF判断は任意 (機能影響ゼロ, 推奨は常時OFF)"),
    bullet("将来TODO: Anthropic Admin Key取得 → usage自動取得 → LINE通知 (Mid優先度)"),
    heading("論点B = 案A 正式確定"),
    para(
        "3点解消により、暫定採用 → 確定に格上げ。月コスト固定 $20、API課金ほぼゼロ、On-Demand Disabled で二重防御。前チャット確定の論点A/C/D (gate_checker系) には影響なし、そのまま実装フェーズに進行可能。"
    ),
    heading("副産物: 6/01-6/04 のAnthropic直接課金 約$220スパイクの再発防止"),
    para(
        "memory既知の mail_pipeline インシデント ($50.88/日) だけでは説明しきれない規模。複数日でスパイクしていた。CostGuard実装 + Cursor移行 + ChatGPT Plus解約で既に再発防止済みだが、Anthropic Console 週次チェック (MODEL_ROUTING.md 第2節) を新規ルール化して二重防御。"
    ),
    heading("壁打ち履歴 (本日累積)"),
    bullet("論点A: GPT-5.5一次 → ジョブズ折衷 → GPT-5.4二次 → GPT-5.4案採用"),
    bullet("論点C: GPT-5.4二次 → GPT-5.5三次 で重大欠陥複数発見"),
    bullet("論点B: GPT-5.4 STOP級指摘 → 実測3点で解消 → 案A正式確定"),
    bullet("→ 共謀リスク対策(型番系列を変える)が本日も有効に機能"),
]

resp = requests.patch(
    f"https://api.notion.com/v1/blocks/{WIKI_BLOCK_ID}/children",
    headers=headers,
    json={"children": children},
    timeout=30,
)

if resp.status_code == 200:
    data = resp.json()
    print("OK Notion SES Wiki 追記成功")
    print(f"   追加ブロック数: {len(data.get('results', []))}")
else:
    print(f"NG Notion API error: {resp.status_code}")
    print(resp.text[:1000])
