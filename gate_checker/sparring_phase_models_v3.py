# -*- coding: utf-8 -*-
"""
Step3 RontenA: phase-model assignment critique-only sparring (v3).
Fix: gpt-5 series consumes reasoning tokens internally. Raise max_completion_tokens
and use reasoning_effort=low to keep text output non-empty.
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os
from pathlib import Path

from openai import OpenAI

BASE = Path(__file__).resolve().parents[1]
env_path = BASE / "config" / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"')

sys.path.insert(0, str(BASE))
from common.ledger import can_spend, daily_total, record

MODEL = "gpt-5.5"
PRICE_IN = 5.0 / 1_000_000
PRICE_OUT = 30.0 / 1_000_000
MAX_OUT = 8000
EST_COST = 3000 * PRICE_IN + MAX_OUT * PRICE_OUT

print("=== RontenA critique sparring v3 ===")
print(f"Model: {MODEL}, max_out={MAX_OUT}")
print(f"Worst-case cost: ${EST_COST:.4f}")
print(f"Today total: ${daily_total():.4f}")

if not can_spend(EST_COST):
    print("[CostGuard] limit reached")
    sys.exit(1)

SYSTEM = """あなたは経営参謀の批判専用カウンセラーです。
必ず以下の構造で応答してください(reasoningは短く、本文を必ず出力):

# 批判
- 問題点1: <具体的に>
  失敗シナリオ: <1行>
- 問題点2: <具体的に>
  失敗シナリオ: <1行>
- 問題点3: <具体的に>
  失敗シナリオ: <1行>

# 代替案
| フェーズ | モデル | 月回数 | 月コスト見積 | 根拠 |
| --- | --- | --- | --- | --- |
(全7フェーズ埋める)

合計月コスト: $X.XX

# 私が間違っている可能性
<1〜2行>
"""

USER = """SES営業会社のCEO参謀AI「ジョブズ」がモデル割振を再設計中。

# 現行単価(2026/6)
- gpt-5.5: $5/$30 per M tokens
- gpt-5.4: $2.50/$15
- gpt-5.4-mini: $0.75/$4.50
- gpt-5.4-nano: $0.20/$1.25
- gpt-5.3-codex: $1.75/$14 (Responses API)

# ジョブズ暫定案
research=nano月5回 / requirements=mini月15 / design=5.4月8 /
pre_impl=mini月15 / implementation=codex月30 / test=5.4月30 / final_gate=5.5月10

# 平均入出力サイズ前提
research/requirements/pre_impl: in 2000 / out 1000
design/test: in 5000 / out 2000
implementation: in 8000 / out 3000
final_gate: in 10000 / out 3000

# 議論したい3論点
1. pre_implを5.4に上げるべきか(見落とし後発見の手戻り大)
2. test月30回を5.4からminiに下げられるか
3. final_gateで本当に5.5が必要か(月10回が高額)

上記システム指示に従い、批判→代替案→自己反省 の構造で応答せよ。
具体的な数字・単価試算を必ず含めること。
"""

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Try with reasoning_effort first
try:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER},
        ],
        max_completion_tokens=MAX_OUT,
        reasoning_effort="low",
    )
    used_param = "reasoning_effort=low"
except Exception as e:
    print(f"reasoning_effort failed: {e}")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER},
        ],
        max_completion_tokens=MAX_OUT,
    )
    used_param = "default"

result = response.choices[0].message.content or ""
usage = response.usage
actual_cost = usage.prompt_tokens * PRICE_IN + usage.completion_tokens * PRICE_OUT
record(usage.prompt_tokens, usage.completion_tokens, MODEL, "sparring_phase_models_v3")

print(f"\nUsed: {used_param}")
print(f"Content length: {len(result)}")
print("=" * 60)
print(result if result else "(EMPTY - reasoning consumed all tokens)")
print("=" * 60)
print(f"Actual cost: ${actual_cost:.4f} (in={usage.prompt_tokens}, out={usage.completion_tokens})")
print(f"Today total: ${daily_total():.4f}")

out_path = BASE / "gate_checker" / "results" / "phase_models_v3_critique.txt"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(
    f"=== v3 critique ({used_param}) ===\n"
    f"in={usage.prompt_tokens} out={usage.completion_tokens} cost=${actual_cost:.4f}\n\n"
    f"{result}\n",
    encoding="utf-8",
)
print(f"Saved: {out_path}")
