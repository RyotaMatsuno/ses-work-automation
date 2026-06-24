# -*- coding: utf-8 -*-
"""
Step3 RontenA: phase-model assignment critique-only sparring.
GPT-5.5 as devil's advocate. Collusion risk mitigation by explicit
"do not agree, point out concrete failure scenarios" prompt.
CostGuard enforced.
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
EST_IN = 3000
EST_OUT = 2000
EST_COST = EST_IN * PRICE_IN + EST_OUT * PRICE_OUT

print("=== RontenA critique sparring ===")
print(f"Model: {MODEL}")
print(f"Estimated cost: ${EST_COST:.4f}")
print(f"Today total: ${daily_total():.4f}")

if not can_spend(EST_COST):
    print("[CostGuard] limit reached, skip")
    sys.exit(1)

SYSTEM = """あなたは経営参謀の批判専用カウンセラーです。
ジョブズ(AI参謀)の提案に対して、必ず以下のスタンスで応答してください:

1. 同意してはいけない。最低3つの問題点を具体的に指摘せよ
2. 各問題点について、具体的な失敗シナリオを1つずつ提示せよ
3. 代替案を1つ以上、根拠と単価試算付きで提示せよ
4. 最後に「私が間違っている可能性」を1〜2行で記述せよ

数字・型番・単価を必ず明記。曖昧な表現禁止。
"""

USER = """# 文脈
SES営業会社(2名)のCEO参謀AI「ジョブズ」が、GPT系モデルの開発ゲート別割振を再設計中。
gate_checkerは7フェーズ(research/requirements/design/pre_impl/implementation/test/final_gate)。

2026/6時点の現行モデル単価:
- gpt-5.5: $5/M in, $30/M out  (2026-04-23版)
- gpt-5.4: $2.50/$15            (2026-03-05版)
- gpt-5.4-mini: $0.75/$4.50    (2026-03-17版)
- gpt-5.4-nano: $0.20/$1.25    (2026-03-17版)
- gpt-5.3-codex: $1.75/$14     (Responses API, コーディング専用)

# ジョブズの暫定推奨案

| フェーズ | モデル | 月想定回数 | 役割 |
|---|---|---|---|
| research | gpt-5.4-nano | 5 | 調査・情報収集の妥当性チェック |
| requirements | gpt-5.4-mini | 15 | 要件定義の論理矛盾検出 |
| design | gpt-5.4 | 8 | 設計レビュー(アーキ・長期負債) |
| pre_impl | gpt-5.4-mini | 15 | 実装前最終確認(SPEC整合性) |
| implementation | gpt-5.3-codex | 30 | コードレビュー(バグ・セキュリティ) |
| test | gpt-5.4 | 30 | テスト結果レビュー(網羅性) |
| final_gate | gpt-5.5 | 10 | デプロイ前最終ゲート |

# ジョブズが議論したい3論点
論点1: pre_implは miniのままでよいか? 5.4に上げるべきか?
       (見落としを後工程で発見すると手戻りコスト大)
論点2: testは月30回で5.4だがminiに下げられるか?
       (テスト結果レビューはチェックリスト的でminiで足りる可能性)
論点3: final_gateで本当に5.5が必要か?
       (月10回×($5/$30)はインパクト大。5.4で代替可能なら年間で大きな差)

# 求める応答
上記システムプロンプトの形式で、具体的に批判してください。
最終的に「ジョブズ案より優れた割振案」を月コスト試算込みで1つ提示してください。
"""

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER},
    ],
    max_completion_tokens=2500,
)

result = response.choices[0].message.content
usage = response.usage
actual_cost = usage.prompt_tokens * PRICE_IN + usage.completion_tokens * PRICE_OUT
record(usage.prompt_tokens, usage.completion_tokens, MODEL, "sparring_phase_models_v2")

print("\n" + "=" * 60)
print("GPT-5.5 critique response")
print("=" * 60)
print(result)
print()
print("=" * 60)
print(f"Actual cost: ${actual_cost:.4f} (in={usage.prompt_tokens}, out={usage.completion_tokens})")
print(f"Today total (updated): ${daily_total():.4f}")
print("=" * 60)

out_path = BASE / "gate_checker" / "results" / "phase_models_v2_critique.txt"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(
    f"=== GPT-5.5 critique sparring result ===\n"
    f"in_tokens: {usage.prompt_tokens}\n"
    f"out_tokens: {usage.completion_tokens}\n"
    f"cost_usd: {actual_cost:.4f}\n\n"
    f"{result}\n",
    encoding="utf-8",
)
print(f"Saved: {out_path}")
