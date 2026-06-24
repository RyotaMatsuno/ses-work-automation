"""
遡及壁打ち: 「Codex移行 vs Cursor維持」のジョブズ独断判断を事後検証
新ルール初適用: 重要判断は必ずGPT壁打ちを通す
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os
from pathlib import Path

from openai import OpenAI

env_path = Path("config/.env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"')

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

CONTEXT = """
# 状況
SES営業自動化システム経営者(松野CEO)が以下の判断を求めた:
「Codex(ChatGPT)に戻そうと思う、ネットで Opus×Codex が最強と見た」

# 経緯
- 2026-06-09: Codex廃止、Cursor移行完了、ChatGPT Plus($20/月)解約済み
- 現在のスタック: Claude Opus 4.8(ジョブズ) + Cursor(実装) + gate_checker(GPT-4o API直叩き)
- 松野の不満: GPT壁打ちが頻発してない、Cursor自動投入が動いてない、物忘れ
- 松野の追加情報: GPT課金を将来必須と考えている、伸びるなら早めに乗り換えたい

# ジョブズの独断判断
「Codex移行は不要、Plus課金も不要、API直叩きでgate_checkerをフェーズ別モデル切替するのが正解」

# 検証してほしい点
1. この判断は本当に正しいか?
2. Codexにしか出来ない事はあるのか?
3. Cursor + Claude Sonnet 4.6 + gate_checker(GPT-4o API)の構成は最適か?
4. 「Opus × Codex最強」記事は松野環境(LINE+Claudeで完結したい・手動最小化)に合うか?
5. 将来GPTが伸びた場合に乗り換え遅れリスクはあるか?
6. ジョブズの「Codex不要」判断に見落としがないか
7. もう一度松野が「やっぱりCodex移行する」と言ったら、どう説得すべきか
"""

PROMPT = f"""
あなたはAI開発スタック設計の専門家。経営者の重要判断を独断したジョブズの判断を事後検証せよ。

{CONTEXT}

【出力形式】
## ジョブズ判断の妥当性(正解/不正解/部分的に正解)
## ジョブズが見落としてる可能性
## Codexにしか出来ない事
## 真の最適スタック構成
## 将来の乗換タイミング判定基準
## もし松野がCodex移行を再提案した時の対応
## 総合判定(独断判断の妥当性スコア 0-100)
"""

print("=" * 60)
print("遡及壁打ち: Codex移行判断の事後検証 (o3)")
print("=" * 60)

response = client.chat.completions.create(
    model="o3",
    messages=[{"role": "user", "content": PROMPT}],
    reasoning_effort="high",
)

result = response.choices[0].message.content
print(result)
print()
cost = response.usage.prompt_tokens * 2 / 1_000_000 + response.usage.completion_tokens * 8 / 1_000_000
print(f"コスト: ${cost:.4f}")
