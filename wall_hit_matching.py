import json

import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
OPENAI_KEY = config.get("OPENAI_API_KEY", "")
GEMINI_KEY = config.get("GEMINI_API_KEY", "")

PROBLEM = """
SES（システムエンジニア派遣）事業のAIマッチングシステムのコスト設計をレビューしてください。

## 実データ（Notion DBから直接取得・検証済み）
- 案件メール: 1日5,000件流入 → 重複除去後ユニーク1,114件/日
- エンジニアDB: 154人
- 1件あたりの実績トークン: 入力6,134tok / 出力1,123tok（Claude Haiku使用時）

## 提案設計: バッチプロンプト方式
現状は「1回のAPI呼び出しで1案件×1エンジニア」を判定（$0.0094/回）。
新設計は「1回のプロンプトにエンジニア1人 + 30案件のスキルリストを詰めて一括判定」。

### バッチプロンプトの入力例:
```
あなたはSESマッチングの専門家です。以下のエンジニアに対し、マッチする案件番号を全て返してください。
エンジニア: Java5年, Spring3年, AWS2年, 単価70万
案件:
1. Java/Spring/AWS 65万
2. Python/Django 60万
...
30. React/TypeScript 70万
回答(番号のみ):
```

### トークン見積もり:
- 入力: 案件30件×30tok + エンジニア150tok + プロンプト200tok = 約1,250tok
- 出力: マッチ番号リスト = 約50tok
- 1回のAPI呼び出し: 入力1,250tok + 出力50tok

### コスト試算（Amazon Nova Micro: 入力$0.035/M, 出力$0.14/M）:
- 1回のコスト: 1250×$0.035/1M + 50×$0.14/1M = $0.0000438 + $0.000007 = $0.0000508
- 1日の呼び出し: 154人 × ceil(1114/30) = 154×38 = 5,852回
- 1日のコスト: 5,852 × $0.0000508 = $0.297/日
- 月のコスト: $0.297 × 30 = $8.9/月

## 質問（正直に指摘してください）
1. バッチプロンプトのトークン見積もり1,250tokは正しいか？案件30件を30tok/件で収まるか？
2. 出力50tokで「マッチ番号リスト」は足りるか？
3. Amazon Nova Microはこの種のスキルマッチング分類タスクに十分な精度を出せるか？
4. この設計に致命的な落とし穴はあるか？
5. 月$150以内に収まるか？見積もりに楽観的な部分はないか？
"""

results = {}

# GPT-5.5
print("=== GPT-5.5に送信中... ===")
try:
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
        json={
            "model": "gpt-5.5",
            "messages": [
                {
                    "role": "system",
                    "content": "あなたはAIシステム設計の専門家です。コスト最適化の観点から厳密にレビューしてください。楽観的な部分があれば必ず指摘してください。",
                },
                {"role": "user", "content": PROBLEM},
            ],
            "max_completion_tokens": 1000,
        },
        timeout=60,
    )
    resp.raise_for_status()
    results["gpt"] = resp.json()["choices"][0]["message"]["content"]
    print("GPT-5.5 OK")
except Exception as e:
    print(f"GPT-5.5 Error: {e}")
    # フォールバック: gpt-4.1-nano
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4.1-nano",
                "messages": [
                    {
                        "role": "system",
                        "content": "あなたはAIシステム設計の専門家です。コスト最適化の観点から厳密にレビューしてください。",
                    },
                    {"role": "user", "content": PROBLEM},
                ],
                "max_tokens": 1000,
            },
            timeout=60,
        )
        resp.raise_for_status()
        results["gpt"] = resp.json()["choices"][0]["message"]["content"]
        print("GPT-4.1-nano OK (fallback)")
    except Exception as e2:
        results["gpt"] = f"GPT Error: {e2}"
        print(f"GPT fallback Error: {e2}")

# Gemini 2.5 Flash
print("\n=== Gemini 2.5 Flashに送信中... ===")
try:
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"あなたはAIシステム設計の専門家です。コスト最適化の観点から厳密にレビューしてください。楽観的な部分があれば必ず指摘してください。\n\n{PROBLEM}"
                        }
                    ]
                }
            ],
            "generationConfig": {"maxOutputTokens": 1000},
        },
        timeout=60,
    )
    resp.raise_for_status()
    results["gemini"] = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    print("Gemini OK")
except Exception as e:
    results["gemini"] = f"Gemini Error: {e}"
    print(f"Gemini Error: {e}")

# 結果表示
for k, v in results.items():
    print(f"\n{'=' * 70}")
    print(f"=== {k.upper()} レビュー結果 ===")
    print(f"{'=' * 70}")
    print(v[:2000])

# 保存
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\wall_hit_result.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
