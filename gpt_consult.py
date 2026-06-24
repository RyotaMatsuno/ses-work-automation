import json
import urllib.request

# GPT-4oに壁打ち
OPENAI_KEY = None
try:
    from dotenv import dotenv_values

    config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
    OPENAI_KEY = config.get("OPENAI_API_KEY")
except:
    pass

problem = """
SES（システムエンジニア派遣）営業の自動マッチングシステムの設計相談。

## 現状と問題
- 案件メール: 1日5,000件流入
- エンジニアDB: 141人（うち提案対象は数十人）
- 現在の実装: 30分おきに「全案件×全エンジニア」総当たりでClaude Haiku APIを呼び出し
- 結果: 1日17,000回API呼び出し → $50/日 → 月$1,500超

## 要件
- エンジニアが来たら合う案件を絞り込んでLINE通知
- 案件は2日以内のもののみ対象（DB内に3,767件）
- キーワード絞り込み後にAI判定でOK
- 予算: 月$150以内（できれば月$50以下）
- 既存エンジニアも1日1回バッチでマッチングしたい

## 質問
月$50以内に収める最も賢い設計は何か？
特に「3,767件の案件DBからキーワード絞り込みで何件まで絞れるか」「既存バッチをどう安くするか」について教えてほしい。
"""

if not OPENAI_KEY:
    print("OPENAI_API_KEY not found")
else:
    data = json.dumps(
        {"model": "gpt-4o", "messages": [{"role": "user", "content": problem}], "max_tokens": 1000}
    ).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read())
    print("=== GPT-4o ===")
    print(res["choices"][0]["message"]["content"])
