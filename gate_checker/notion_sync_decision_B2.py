#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Notion SES Wiki append rontenB"""

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


def heading(text, level=2):
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
    heading("2026-06-16 論点B確定: Cursor統合戦略 = 案A(現状維持)", 2),
    para(
        "前チャットでは『Cursor Free Plan + APIキー直挿し』を前提に案A/B/Cを比較していた。本日Cursor設定UIのスクショで前提が崩れたため、再評価を実施。"
    ),
    heading("判明した事実(スクショ実測)", 3),
    bullet("Current Plan: Pro $20/mo (リセット日 7/9)"),
    bullet("Included in Pro 含有枠消費率: Total 6% (7日経過時点)。線形換算で月末 ~26% 消費見込み。74% 余裕あり"),
    bullet("内訳: 8% Auto / 0% API used → Anthropic Key ON だが実際にはAPI経由の課金ゼロ"),
    bullet("On-Demand Spending: Disabled (超過時自動課金OFF。リスク遮断済み)"),
    bullet("UPGRADE AVAILABLE: Pro+ $60/mo (3倍枠)が表示されるが現状では不要"),
    heading("判断", 3),
    para("案A (Cursor Pro $20/月 継続) で確定。月コスト固定 $20、API課金なし。"),
    bullet("案B (Sonnet 4.6 + gpt-5.3-codex 併用): codex従量分が乗るため増額。現状で枠余ってるので不要"),
    bullet("案C (Cursor Pro 解約 + 全GPT API): Pro $20 含有枠を捨てる損。不要"),
    heading("付随アクション", 3),
    bullet(
        "推奨(任意): Cursor設定の Anthropic API Key を OFF にする。現状0%なので機能影響ゼロ。Pro超過時の自動API課金リスクを排除し、On-Demand Disabled と二重防御に"
    ),
    bullet("Pro+/Ultra アップグレード: 不要"),
    bullet("View All Models で gpt-5.3-codex 探す: 不要(統合自体しないため)"),
    heading("前チャット確定事項への影響", 3),
    para(
        "論点A/C/D は gate_checker系(OpenAI API直接呼出)であり Cursor とは独立系統。本日の論点B変更による影響なし。前チャット確定の実装計画(フェーズ別モデル割振・DAILY_CALL_LIMIT段階値・二次壁打ち分離アプローチ・安全装置4つロードマップ)はそのまま進行可能。"
    ),
    heading("壁打ち実施有無", 3),
    para(
        "壁打ち不要と判断。理由: スクショ実測値で数字が一意に決まり、推論余地がない(消費率6%, API 0%, On-Demand Disabled)。ジョブズの古い知識(Free Plan前提)が崩れた瞬間に Cursor 公式 pricing と松野UIで再ベースライン化済み。"
    ),
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
