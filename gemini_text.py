# -*- coding: utf-8 -*-
# Gemini 再度全文取得（レスポンス形式変更）
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
GEMINI_KEY = env.get("GEMINI_API_KEY", "")

context = """
TERRA SES事業のAnthropicコスト調査です。
日別コスト推移: 5/26=$0.03, 5/27=$0.85, 6/9=$0.09, 6/10=$0.004, 6/11=$1.90, 6/12=$0.62, 6/14=$2.10, 6/15=$3.97
6月累計（15日時点）=$8.68、上限$140設定

今日の事象:
- matching_v2でJSONDecodeError多発（max_tokens 4000不足→8000に修正済み）
- mail_pipeline誤設定で30分×16回実行（本来は朝1回→修正済み）
- Anthropicオートチャージ（プリペイド残高枯渇）が今日発動

質問:
1. 今日のオートチャージは誤設定バグが原因か、たまたま今日が課金タイミングか
2. 同様の事態が再発するリスクと穴
3. アラートKPIと閾値の推奨
4. 実装すべきアラートの優先順位

テキストで端的に回答してください（JSON不要）"""

r = requests.post(
    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}",
    headers={"Content-Type": "application/json"},
    json={"contents": [{"parts": [{"text": context}]}], "generationConfig": {"maxOutputTokens": 1500}},
    timeout=60,
)
if r.status_code == 200:
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    print(text)
else:
    print(f"エラー: {r.status_code} {r.text[:200]}")
