# -*- coding: utf-8 -*-
"""
Notion: append decision log to SES knowledge Wiki page,
and add long-term TODOs to AI work queue DB.
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parents[1]
env_path = BASE / "config" / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")

TOKEN = os.environ["NOTION_API_KEY"]
WIKI_BLOCK = "353450ff-37c0-8145-9e3e-d80c8c8ed594"
QUEUE_DB = os.environ["NOTION_AI_QUEUE_DB_ID"]

H = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def text(content):
    return {"type": "text", "text": {"content": content}}


def block_h2(t):
    return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [text(t)]}}


def block_h3(t):
    return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": [text(t)]}}


def block_p(t):
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [text(t)]}}


def block_bul(t):
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [text(t)]}}


# === 1. ナレッジWikiにdecision log追記 ===
children = [
    block_h2("2026-06-16 gate_checker再設計 確定事項"),
    block_p(
        "Sonnet 4.6 + Opus 4.8で実施、4ラウンド壁打ち(GPT-5.5/5.4/5.5)で結論。本日壁打ちコスト$0.21、CostGuard内余裕大。"
    ),
    block_h3("論点A: フェーズ別モデル割振(確定)"),
    block_bul("research=gpt-5.4-mini / requirements=gpt-5.4-mini"),
    block_bul("design=gpt-5.4 / pre_impl=gpt-5.4"),
    block_bul("implementation=gpt-5.3-codex (Responses API)"),
    block_bul("test=gpt-5.4 / final_gate=gpt-5.4"),
    block_bul("合計113回/月、月コスト $3.94"),
    block_bul("gpt-5.5は完全別管理。ジョブズが明示判定した時のみ手動呼出(年数回)"),
    block_h3("論点D: 安全装置4つ段階実装ロードマップ(確定)"),
    block_bul("Week1: 装置2(リクエスト超過警告フェーズ別閾値版)+装置3(CostGuard停止時Notionキュー)"),
    block_bul("Week2: 装置1(ledger.py外挿検知。前回比2倍超でLINE警告)"),
    block_bul("Week3-4: 装置4(自動ロールバック。limit_controller.py新規)"),
    block_bul("装置2閾値:research/req/pre_impl/test=$0.025, design=$0.10, implementation=$0.15, final_gate=$0.15"),
    block_h3("論点C: DAILY_CALL_LIMIT・二次壁打ち設計(確定)"),
    block_bul("DAILY_CALL_LIMIT: 30→60→90 (110保留)。worst-case単価$0.070でCostGuard内に収まる設計"),
    block_bul("対象範囲: gate_checker系のみ。mail_pipeline/matching_v3は別カウント(CostGuard全体監視)"),
    block_bul(
        "二次壁打ち発動: design全件 / final_gate=タグ判定(売上・契約・法務・freee・送信系) / implementation=キーワード判定(権限・課金・認証・個人情報・送信先・SQL条件変更)"
    ),
    block_bul("二次モデル: gpt-5.4-mini ($0.75/$4.50)"),
    block_bul("解放条件: 14日連続で消費率<50% + サンプリング監査5件中5件OK"),
    block_bul("fail-closed対象: 契約・請求・個人情報・外部送信 / fail-open対象: 内部要約・調査"),
    block_bul("月コスト総額見込み: $4.14/月 (CostGuard $140/月の3%)"),
    block_h3("論点B: Cursor統合戦略(判断保留)"),
    block_bul("Anthropic現行: Sonnet 4.6=$3/$15, Opus 4.8=$5/$25, Haiku 4.5=$1/$5"),
    block_bul("コスト比較: gpt-5.3-codex ($1.75/$14) は Sonnet 4.6 より約40%安"),
    block_bul(
        "次チャット松野アクション: Cursor設定UIで①複数プロバイダー登録可否②モデル切替挙動③custom model追加可否を確認"
    ),
    block_bul("判断は次チャット(Opus 4.8推奨)で実施"),
    block_h3("壁打ち履歴(本日)"),
    block_bul("GPT-5.5 一次批判(論点A): $0.047"),
    block_bul("GPT-5.4 二次批判(論点A): $0.052"),
    block_bul("GPT-5.4 一次批判(論点C): $0.041"),
    block_bul("GPT-5.5 三次批判(論点C): $0.116"),
    block_bul(
        "ROI: 共謀リスク対策で運用設計の重大欠陥複数発見(GPT-5.5の単独提案は警告0件解放条件のGoodhart's law発症リスクあり、ジョブズ折衷案はrisk_score未設計・mini二次壁打ちで品質逆転リスクあり、を発見)"
    ),
]

print("=" * 60)
print("Notion Wiki append")
print("=" * 60)

url = f"https://api.notion.com/v1/blocks/{WIKI_BLOCK}/children"
r = requests.patch(url, headers=H, json={"children": children})
print(f"status: {r.status_code}")
if r.status_code != 200:
    print(r.text[:1500])
else:
    print(f"Appended {len(children)} blocks to Wiki.")

# === 2. AI作業キューDBに法人化後TODO 6件を登録 ===
print()
print("=" * 60)
print("Notion AI work queue: long-term TODOs")
print("=" * 60)

todos = [
    "三層化:gate_checker専用予算リザーブの設計",
    "risk_score算出モジュールの仕様化(独立モジュール、根拠ログ必須)",
    "二次モデルの高リスク領域での昇格ルール(mini→5.4→5.5/人間承認)",
    "利用者別quota・監査ログ・override承認フローの設計",
    "プロンプト・評価観点・禁止基準の独立性設計(系列分離だけでなく観点分離)",
    "営業サイクル(月末・締め日・契約更新)を考慮した動的quota設計",
]

# DBスキーマを取得して必須プロパティを確認
db_url = f"https://api.notion.com/v1/databases/{QUEUE_DB}"
r = requests.get(db_url, headers=H)
print(f"DB schema status: {r.status_code}")
if r.status_code == 200:
    props = r.json().get("properties", {})
    title_prop = None
    for name, info in props.items():
        if info.get("type") == "title":
            title_prop = name
            break
    print(f"Title prop: {title_prop}")
    print(f"Available props: {list(props.keys())[:20]}")

    for i, todo in enumerate(todos, 1):
        body = {
            "parent": {"database_id": QUEUE_DB},
            "properties": {
                title_prop: {"title": [text(f"[法人化後TODO] {todo}")]},
            },
        }
        # 状態・優先度・担当があれば設定
        if "状態" in props and props["状態"]["type"] == "status":
            body["properties"]["状態"] = {"status": {"name": "queued"}}
        elif "状態" in props and props["状態"]["type"] == "select":
            body["properties"]["状態"] = {"select": {"name": "queued"}}
        if "優先度" in props and props["優先度"]["type"] == "select":
            body["properties"]["優先度"] = {"select": {"name": "Low"}}
        if "担当" in props and props["担当"]["type"] == "select":
            body["properties"]["担当"] = {"select": {"name": "jobz"}}
        if "種別" in props and props["種別"]["type"] == "select":
            body["properties"]["種別"] = {"select": {"name": "後日タスク"}}

        cr = requests.post("https://api.notion.com/v1/pages", headers=H, json=body)
        if cr.status_code == 200:
            print(f"  [{i}/6] OK: {todo[:50]}")
        else:
            print(f"  [{i}/6] FAIL ({cr.status_code}): {cr.text[:300]}")
            # 失敗した場合はプロパティを減らして再試行
            if cr.status_code == 400:
                simple_body = {
                    "parent": {"database_id": QUEUE_DB},
                    "properties": {title_prop: {"title": [text(f"[法人化後TODO] {todo}")]}},
                }
                cr2 = requests.post("https://api.notion.com/v1/pages", headers=H, json=simple_body)
                print(f"     retry simple: {cr2.status_code}")
                if cr2.status_code != 200:
                    print(f"     {cr2.text[:300]}")
else:
    print(r.text[:500])

print()
print("=== Notion sync complete ===")
