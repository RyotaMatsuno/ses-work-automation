"""
壁打ちラウンド3: o3で最終決着
GPT-4o(保守派) vs o3-mini(ハイブリッド派)の分裂を裁定
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
SES営業自動化システムの「フェーズ別モデル割振」について、2つのAIで意見が割れた。
あなたは最終裁定者として、最も合理的な構成を確定せよ。

【背景】
- 経営者(松野)はAI壁打ちフローを大量回転させたい(1日5タスク × 6工程 × 8往復 = 240回/日)
- 現状: 全工程gpt-4o → 月$80-120
- 経営者のリスク許容度: 中(コスト暴走経験あり、ただし品質低下も嫌う)

【意見1: GPT-4o(保守的)】
research以外は全部gpt-4o。コストよりリスク回避優先。月$100-150。

【意見2: o3-mini(ハイブリッド派)】
research/requirements/pre_impl/testはmini、designはo3-mini、implementationは4o、final_gateはo3。
月$30-50。

【あなたへの指示】
1. SES営業文脈で本当にminiで事故るフェーズを特定せよ
2. 推論モデル(o3系)を使う価値があるフェーズを特定せよ
3. 「1工程8往復」のうち、最初の数往復は安いモデルで広く探索、後半は推論モデルで深掘り、という階層設計は妥当か?
4. 最終確定案を出せ(逃げ・両論併記禁止、必ず1つに絞れ)
5. 想定月コストを根拠付きで計算せよ
6. 「ここは絶対譲るな」というポイントを1つ挙げよ

出力形式:
## 裁定結論(3行)
## 各フェーズ確定モデル(表形式)
## 月コスト試算(根拠付き)
## 絶対に守るべきポイント
"""

print("=" * 60)
print("壁打ちラウンド3: o3による最終裁定")
print("=" * 60)

response = client.chat.completions.create(
    model="o3",
    messages=[{"role": "user", "content": PROMPT}],
    reasoning_effort="high",
)

result = response.choices[0].message.content
print(result)
print()
print("=" * 60)
print(f"使用トークン: in={response.usage.prompt_tokens} / out={response.usage.completion_tokens}")
cost = response.usage.prompt_tokens * 2 / 1_000_000 + response.usage.completion_tokens * 8 / 1_000_000
print(f"今回コスト: ${cost:.4f}")
print("3ラウンド合計コスト: 約$0.025")
print("=" * 60)
