# -*- coding: utf-8 -*-
"""
Step3 RontenA: secondary critique by GPT-5.4.
Target: jobz compromise plan (incorporates GPT-5.5 critique).
Goal: find blind spots in the compromise itself (collusion risk mitigation).
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

MODEL = "gpt-5.4"
PRICE_IN = 2.5 / 1_000_000
PRICE_OUT = 15.0 / 1_000_000
MAX_OUT = 6000
EST_COST = 3000 * PRICE_IN + MAX_OUT * PRICE_OUT

print(f"=== RontenA secondary critique by {MODEL} ===")
print(f"Worst-case cost: ${EST_COST:.4f}")
print(f"Today total: ${daily_total():.4f}")

if not can_spend(EST_COST):
    print("[CostGuard] limit reached")
    sys.exit(1)

SYSTEM = """あなたは二次批判の専門カウンセラーです。
GPT-5.5(別世代)が一次批判をした後、ジョブズ(AI参謀)が折衷案を作りました。
あなたの役割は折衷案そのものを批判することです。
GPT-5.5に同調してはいけません。GPT-5.5の批判が見落とした盲点を探してください。

必ず以下の構造で応答:

# 折衷案の脆い前提(3つ)
1. <前提>: なぜ脆いか / 崩れた場合の損失
2. <前提>: なぜ脆いか / 崩れた場合の損失
3. <前提>: なぜ脆いか / 崩れた場合の損失

# GPT-5.5の批判で見落とされた論点(2つ以上)
- <論点>: <理由>
- <論点>: <理由>

# 最終推奨案(あなたの判断)
| フェーズ | モデル | 月コスト | 根拠 |
(7フェーズ埋める)

合計月コスト: $X.XX

# 確信度
1〜5(5が最も確信)で自己評価。なぜその値か1行。
"""

USER = """# 経緯
GPT-5.5が一次批判で、ジョブズ初案に対して以下3点を指摘した:
- pre_impl は mini→5.4 に上げるべき(後工程手戻り防止)
- test は 5.4→mini に下げて良い(チェックリスト的タスク)
- final_gate は全件5.5でなく、5.4ベース+例外のみ5.5

# ジョブズの折衷案(あなたが批判する対象)
| フェーズ | モデル | 月回数 | 月コスト | 切替条件 |
| --- | --- | ---: | ---: | --- |
| research | gpt-5.4-nano | 5 | $0.008 | - |
| requirements | gpt-5.4-mini | 15 | $0.09 | - |
| design | gpt-5.4 | 8 | $0.34 | - |
| pre_impl | gpt-5.4 | 15 | $0.30 | GPT-5.5案採用 |
| implementation | gpt-5.3-codex | 30 | $1.68 | - |
| test | gpt-5.4-mini | 30 | $0.38 | 新規テスト追加/大規模リファクタ時のみ5.4 |
| final_gate | gpt-5.4 | 10 | $0.56 | ハイリスク条件のみ5.5 |

合計: $3.36/月

# ハイリスク条件の定義(final_gateで5.5に切替える条件)
- 送信系の自動化(メール・LINE送信ロジック変更)
- DB破壊的変更(マイグレーション・スキーマ変更)
- freee請求確定ロジック
- 契約マスター変更ロジック
- 認証・トークン管理変更

# あなたの仕事
上記折衷案の盲点を探せ。GPT-5.5の批判は前提として既知だから、それと違う角度から指摘せよ。
特に注目すべき点:
- 「切替条件」の運用が現場で機能するか
- 月回数の見積もりは妥当か
- フェーズ間の連携(出力がどこに流れるか)で問題は無いか
- モデル切替自体のオーバーヘッド(コード複雑化)は考慮されているか

数字・型番を必ず明記。曖昧表現禁止。
"""

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

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
    used = "reasoning_effort=low"
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
    used = "default"

result = response.choices[0].message.content or ""
usage = response.usage
actual_cost = usage.prompt_tokens * PRICE_IN + usage.completion_tokens * PRICE_OUT
record(usage.prompt_tokens, usage.completion_tokens, MODEL, "sparring_phase_models_secondary")

print(f"\nUsed: {used}")
print(f"Content length: {len(result)}")
print("=" * 60)
print(result if result else "(EMPTY)")
print("=" * 60)
print(f"Actual cost: ${actual_cost:.4f} (in={usage.prompt_tokens}, out={usage.completion_tokens})")
print(f"Today total: ${daily_total():.4f}")

out_path = BASE / "gate_checker" / "results" / "phase_models_secondary_critique.txt"
out_path.write_text(
    f"=== secondary critique by {MODEL} ({used}) ===\n"
    f"in={usage.prompt_tokens} out={usage.completion_tokens} cost=${actual_cost:.4f}\n\n"
    f"{result}\n",
    encoding="utf-8",
)
print(f"Saved: {out_path}")
