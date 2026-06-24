#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Notion SES Wiki に $220 真因と Admin Key タスク登録の追記"""

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
    heading("2026-06-16 追補1: 6/01-04 約$220スパイクの真因確定", 2),
    para("松野からの追加情報で真因が判明。ジョブズの初期解釈(mail_pipelineインシデント単独)は不正確だったため修正。"),
    heading("真因(松野証言)"),
    bullet("6/01-04のAnthropic直接課金スパイク約$220は2つの要因の合算"),
    bullet("要因A: 2026-06-02の mail_pipeline インシデント ($50.88/日, FETCH_LIMIT上限なし+重複処理)"),
    bullet("要因B: Claude.ai (Claude Pro月額) のチャットトークン枠不足のためのトークン追加購入 (松野が意図的に実施)"),
    bullet("→ 要因Bは「再発リスク」ではなく松野の合理的な意思決定による追加支出"),
    heading("再発防止の評価修正"),
    para("修正前(ジョブズ初期解釈): 「全てインシデント由来。Anthropic Console 週次チェックで再発防止が必要」"),
    para(
        "修正後: 「mail_pipeline型のインシデントはCostGuard+Cursor移行で防止済み。Claude.aiトークン購入型は意図的支出で問題なし。Cursor完全移行(6/09)後はClaude.ai自体の依存が下がり、トークン購入も発生していない」"
    ),
    heading("Anthropic Console 週次チェックは継続"),
    para(
        "$220スパイクの再発リスクは低いが、Anthropic Console 週次チェック (MODEL_ROUTING.md 第2節) は別の理由でも有益なため継続:"
    ),
    bullet("Cursor経由実装の Anthropic 課金内包仕様が将来変わる可能性"),
    bullet("CostGuard外の経路でAPI呼び出しが起きる将来リスクの早期検知"),
    bullet("Claude Code / Claude Cowork など別ツール導入時の課金把握"),
    heading("2026-06-16 追補2: Anthropic Admin Key 自動化タスク正式登録"),
    para("松野指示によりNotion AI作業キューDBに正式登録。task_id: anthropic_admin_key_automation_20260616"),
    bullet("優先度: Mid / 担当: jobz / 状態: queued"),
    bullet(
        "内容: Anthropic Admin API (v1/organizations/usage_report/messages, v1/organizations/cost_report)で日次使用量自動取得"
    ),
    bullet("統合: common/ledger.py と連携し、Cursor Pro / OpenAI / Anthropic 三系統の統合監視に拡張"),
    bullet("通知: 異常値(1日$10超)で LINE 通知"),
    bullet("前提作業: 松野が console.anthropic.com → Settings → API Keys → Create Admin Key を実施"),
    bullet("コスト見込み: 開発時APIコスト約$1"),
    heading("ジョブズの自己レビュー"),
    para(
        "今日の学び: ジョブズが「Anthropicスパイクの再発防止が必要」と判断したが、松野の追加情報で正確な真因が判明した。「実測データだけで因果を確定」してしまうリスクの実例。次回類似ケースでは『ジョブズの解釈』を松野に明示し、誤解修正の機会を作る運用にする。"
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
    print("OK Notion SES Wiki 追記成功 (追補1+2)")
    print(f"   追加ブロック数: {len(data.get('results', []))}")
else:
    print(f"NG Notion API error: {resp.status_code}")
    print(resp.text[:1000])
