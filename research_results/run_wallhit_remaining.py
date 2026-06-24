import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from openai import OpenAI
from dotenv import dotenv_values

env_path = os.path.join(os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work", "config", ".env")
env = dotenv_values(env_path)
client = OpenAI(api_key=env.get("OPENAI_API_KEY"))

prompt = """SES自動化システムの残タスク整理と次のアクション決定。日本語で。

## 今日完了済み（15タスク）
A: BTM/NBW案件取りこぼし修正
B: Notion登録失敗リトライ
C: CostGuard v2統合（fail-close）
D: 語彙外スキルREVIEW化
E: soft-skill all-pass + Ruff/pyright導入
F: freee monthly退役 + FT階段粗利
G: SQLite WAL + IMAPタイムアウト
I: 備考日数分岐 + human_reviewキーワード
K: PROCESS_LIMIT=100引き上げ

## Cursor進行中（2タスク）
L: 分類精度改善（other→project漏れ。141件の案件がother判定。最優先）
M: gate_checker Gemini→Claude Sonnet差し替え

## 未投入（2タスク）
H: LINE push -1バグ修正 + UTC/JST日付境界修正
J: gate_checker v2.2（scheduler統廃合 + プロンプト改善）

## 新たに判明した問題
1. LINE月次push上限到達（残0通）→ 7月リセットまでpush不可。reply-onlyモードは正常動作
2. 分類精度問題: 549件中379件がother。案件141件がNotion未登録。Task Lで対処中
3. Gemini無料枠完全枯渇→ Task Mで対処中

## 元の20件リストで未対応
7: 並行情報の当日確認チェック（松野が「7以外全部」と指示→除外）
包括レポート提言: llm_gateway単一入口、tenacity/pybreaker統一、asyncio並列化、Notionキャッシュ

## 質問
Q1: H/Jの投入タイミング。L/M完了を待つべきか、並列でいいか？
Q2: Task L完了後、other判定の141件を再処理する際の注意点は？コスト増を試算。
Q3: 包括レポートの構造改善（llm_gateway等）はいつ着手すべきか？Task L/Mの後か、もっと先か？
Q4: 月末（7月請求前）までにやるべきタスクの最終リストを出して。
Q5: 今日1日で15タスク完了＋2タスク進行中。このペースで来週何を目指すべきか？"""

print("o4-miniに壁打ち中...", flush=True)
resp = client.responses.create(
    model="o4-mini",
    input=[{"role": "user", "content": prompt}],
    reasoning={"effort": "medium"},
    max_output_tokens=6000
)
full_text = ""
for item in resp.output:
    if item.type == "message":
        for part in item.content:
            if hasattr(part, "text"):
                full_text += part.text
print(full_text)

out_path = os.path.join(os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work", "research_results", "GPT_WALLHIT_REMAINING.md")
with open(out_path, 'w', encoding='utf-8') as f:
    f.write("# GPT壁打ち: 残タスク整理\n実行日: 2026-06-19\n\n")
    f.write(full_text)
print(f"\n保存: {out_path}")
