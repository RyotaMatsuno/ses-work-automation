# -*- coding: utf-8 -*-
# Gemini全文取得
import json
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
GEMINI_KEY = env.get("GEMINI_API_KEY", "")

context = """
日別コスト: 5/26=$0.03, 5/27=$0.85, 6/9=$0.09, 6/10=$0.004, 6/11=$1.90, 6/12=$0.62, 6/14=$2.10, 6/15=$3.97（今日）
月別: 5月=$0.88、6月15日時点=$8.68
今日の事象: matching_v2でJSONDecodeError多発（max_tokens不足→修正済み）、mail_pipeline30分×16回（誤設定→修正済み）、Anthropicオートチャージ発動
CostGuard: 日次$8/月次$140でledger.pyが推定管理するが、Anthropicの実残高とは別管理

以下をJSON形式で回答してください:
{
  "autocharge_verdict": "たまたま or コスト超過が原因",
  "autocharge_reason": "詳細",
  "recurring_risk": "今後も同様のオートチャージが起きるリスクの評価",
  "management_holes": ["穴1","穴2",...],
  "alert_kpis": [{"metric":"","threshold":"","reason":""}],
  "alert_implementation": "LINEアラートの実装方針",
  "recommendations": ["推奨1","推奨2",...]
}"""

r = requests.post(
    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}",
    headers={"Content-Type": "application/json"},
    json={"contents": [{"parts": [{"text": context}]}], "generationConfig": {"maxOutputTokens": 2000}},
    timeout=60,
)
if r.status_code == 200:
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    # jsonブロック抽出
    import re

    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(0))
            print(json.dumps(parsed, ensure_ascii=False, indent=2))
        except:
            print(text[:2000])
    else:
        print(text[:2000])
else:
    print(f"エラー: {r.status_code} {r.text[:200]}")
