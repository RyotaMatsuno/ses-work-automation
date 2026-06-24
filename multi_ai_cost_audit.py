# -*- coding: utf-8 -*-
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
OPENAI_KEY = env.get("OPENAI_API_KEY", "")
GEMINI_KEY = env.get("GEMINI_API_KEY", "")
ANTHROPIC_KEY = env.get("ANTHROPIC_API_KEY", "")

context = """
【TERRA SES事業 APIコスト調査 - 調査データ】

■ システム概要
- 2名体制のSES事業者
- mail_pipeline.py: 30分おき実行、3アカウントからメール取得・LLMで分類・Notionに登録
- matching_v2/v3: SESマッチングエンジン
- CostGuard: 日次$8/月次$140の上限管理（ledger.pyで実装）

■ 実測コストデータ（cost_log.jsonlより）
日別コスト:
  2026-05-26: $0.03（9コール）
  2026-05-27: $0.85（138コール）
  2026-06-09: $0.09（313コール）
  2026-06-10: $0.004（11コール）
  2026-06-11: $1.90（1032コール）
  2026-06-12: $0.62（327コール）
  2026-06-14: $2.10（997コール）
  2026-06-15: $3.97（2025コール）★今日

月別合計:
  2026-05: $0.88
  2026-06（15日時点）: $8.68

スクリプト別累計:
  mail_pipeline: $7.86（全体の90%）
  matching_v2: $0.87
  skill_reader: $0.44
  その他: $0.38

■ 今日の詳細
- Anthropic haiku: 1800コール、入力185万トークン、出力46万トークン
- ledger記録: $3.97
- 公式レート再計算: $4.76（差異$0.79）

■ 今日発生したこと
1. matching_v2でJSONDecodeError連発（max_tokens 4000不足→今日8000に修正済み）
2. mail_pipelineが30分×16回実行（2時間おきに誤設定→今日修正済み）
3. Anthropicオートチャージ発動（残高が尽きて自動課金）

■ CostGuardの仕組み
- ledger.py: 推定コストで日次$8/月次$140を管理
- 実際のAnthropicプリペイド残高とは別管理
- Monthly Spend Limitの設定状況: 不明（Consoleで確認必要）

■ 質問
以下について分析・評価してください：
1. 今日のオートチャージは「たまたま今日が課金タイミング」か「コスト超過が原因」か
2. ledger.pyとAnthropicの実請求に差異が生じる原因と問題度
3. 現在のコスト管理に穴や見落としはないか
4. コストアラートの実装で何を監視すべきか（KPIと閾値）
5. 月$140上限内で安全に運用するための改善提案

JSON形式で回答:
{
  "autocharge_verdict": "たまたま or コスト超過",
  "autocharge_reason": "",
  "ledger_gap_risk": "high/medium/low",
  "ledger_gap_cause": "",
  "management_holes": [],
  "alert_kpis": [{"metric":"","threshold":"","reason":""}],
  "recommendations": []
}
"""


def call_gpt(prompt):
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
        json={
            "model": "gpt-4o",
            "max_tokens": 1500,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    if r.status_code == 200:
        return "GPT-4o", r.json()["choices"][0]["message"]["content"]
    return "GPT-4o", f"エラー: {r.status_code}"


def call_gemini(prompt):
    if not GEMINI_KEY:
        return "Gemini", "API_KEY未設定"
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1500, "responseMimeType": "application/json"},
        },
        timeout=60,
    )
    if r.status_code == 200:
        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return "Gemini-2.5-Flash", text
    return "Gemini-2.5-Flash", f"エラー: {r.status_code} {r.text[:100]}"


results = {}
with ThreadPoolExecutor(max_workers=2) as ex:
    futures = {ex.submit(call_gpt, context): "gpt", ex.submit(call_gemini, context): "gemini"}
    for f in as_completed(futures):
        name, text = f.result()
        results[name] = text
        print(f"\n=== {name} ===")
        try:
            parsed = json.loads(text)
            print(json.dumps(parsed, ensure_ascii=False, indent=2))
        except:
            print(text[:1000])
