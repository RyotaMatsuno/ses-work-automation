"""
GPT-4o壁打ちラウンド2: o3-mini視点で同じ提案をレビュー
推論モデルなら違う答えが出るか検証
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

PROMPT = """
あなたは推論重視のAI設計レビュアー。GPT-4oが「全部gpt-4oにせよ」と保守的回答した。
これを批判的にレビューせよ。

【元の提案】(ジョブズ案)
- research → gpt-4o-mini
- requirements → gpt-4o-mini
- design → o3-mini
- pre_impl → gpt-4o-mini
- implementation → gpt-4o
- test → gpt-4o-mini
- final_gate → o3

【GPT-4oラウンド1の結論】
研究以外は全部gpt-4oにせよ。コストよりリスク回避優先。

【規模】1日240回API呼出。月コスト想定:
- ジョブズ案: $30-50
- GPT-4oラウンド1案: $100-150

【批判観点】
1. GPT-4o案は「全部4o」でコスト3倍になるが、本当にminiでは事故るのか?
2. requirementsの「形式チェック」はminiで十分なはず。4o使う合理性は?
3. designに4o vs o3-mini どちらが推論深いか?(2026年6月時点の実性能)
4. 「1工程8往復」設計の合理性
5. 推論モデル(o3系)を使うべきフェーズはどこか
6. mini使うのが妥当なフェーズはどこか

出力形式:
## GPT-4oラウンド1への反論
## 推論モデル視点の再評価
## minionly使うべきフェーズ
## o3-only使うべきフェーズ
## 最終推奨構成(モデル名+月コスト試算)
"""

print("=" * 60)
print("壁打ちラウンド2: 推論モデル視点での反論")
print("=" * 60)

# o3-miniを使う(reasoning_effortパラメータあり)
response = client.chat.completions.create(
    model="o3-mini",
    messages=[{"role": "user", "content": PROMPT}],
    reasoning_effort="medium",
)

result = response.choices[0].message.content
print(result)
print()
print("=" * 60)
print(f"使用トークン: in={response.usage.prompt_tokens} / out={response.usage.completion_tokens}")
cost = response.usage.prompt_tokens * 1.1 / 1_000_000 + response.usage.completion_tokens * 4.4 / 1_000_000
print(f"今回コスト: ${cost:.4f}")
print("=" * 60)
