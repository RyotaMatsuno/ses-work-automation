import json
import urllib.request

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
GEMINI_KEY = config.get("GEMINI_API_KEY") or config.get("GOOGLE_API_KEY")

problem = """
SES（システムエンジニア派遣）事業のAIマッチングシステムのコスト設計をレビューしてください。

## 実データ（検証済み）
- 案件メール: 1日約1,883件（2日で3,767件がNotionに登録されている）
- 重複除去後: 2,228件/2日 → 約1,114件/日ユニーク
- エンジニアDB: 143人
- 人材メール: 1日約20件
- スキルタグなし案件: 全体の52%

## 提案アーキテクチャ
1段目: 重複除去（ハッシュ、無料）
2段目: embedding（ruri-v3ローカル、無料）でエンジニアスキル×案件を類似度計算し上位N件抽出
3段目: 安いLLM（Gemini 2.5 Flash-Lite or Nova Micro）でスキル精密判定

## 確認済み料金（複数ソースクロスチェック済み）
- Gemini 2.5 Flash-Lite: 入力$0.10/M, 出力$0.40/M (Batch 50%off)
- GPT-4.1 Nano: 入力$0.10/M, 出力$0.40/M (Batch 50%off)
- Amazon Nova Micro: 入力$0.035/M, 出力$0.14/M (Batch 50%off)
- Claude Haiku 4.5（現行）: 入力$1.00/M, 出力$5.00/M

## 試算
実績トークン: 入力6,134tok/回, 出力1,123tok/回
embedding上位10件に絞った場合: 1,114案件×10人 = 11,140回/日
- Gemini Flash-Lite Batch: $0.000531/回 × 11,140 = $5.92/日 → 月$178
- Nova Micro Batch: $0.000186/回 × 11,140 = $2.07/日 → 月$62

## 質問
1. この試算に漏れ・間違いはあるか？
2. embeddingで上位10件に絞る前提は現実的か？スキルタグなし52%の案件はどう扱うべきか？
3. Batch APIの24時間制約はSES営業（即時性重要）に問題はないか？
4. 他にコスト削減の余地はあるか？
5. 月$150以内に確実に収めるにはどの設計がベストか？
"""

data = json.dumps(
    {"contents": [{"parts": [{"text": problem}]}], "generationConfig": {"maxOutputTokens": 1500}}
).encode()

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

with urllib.request.urlopen(req, timeout=30) as r:
    res = json.loads(r.read())

text = res["candidates"][0]["content"]["parts"][0]["text"]
print("=== Gemini 2.5 Flash-Lite レビュー ===")
print(text)
