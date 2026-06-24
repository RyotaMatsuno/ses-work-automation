# -*- coding: utf-8 -*-
"""
Step3 RontenC: DAILY_CALL_LIMIT and collusion mitigation cost critique.
GPT-5.4 critique-only sparring.
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
EST_COST = 3500 * PRICE_IN + MAX_OUT * PRICE_OUT

print(f"=== RontenC critique by {MODEL} ===")
print(f"Worst-case cost: ${EST_COST:.4f}")
print(f"Today total: ${daily_total():.4f}")

if not can_spend(EST_COST):
    print("[CostGuard] limit reached")
    sys.exit(1)

SYSTEM = """あなたは批判専用カウンセラーです。SES事業のコスト構造設計をレビューします。
必ず以下の構造で応答(reasoningは短く、本文を必ず出力):

# 提案の脆い前提(3つ以上)
- 前提: <具体的に> / 崩れた場合の損失: <具体>

# 数値設計の問題点
- 段階値の妥当性
- 二次壁打ち発動条件の妥当性
- コスト試算の漏れ

# 別観点での代替案
| 項目 | 提案案 | 代替案 | 根拠 |
(段階値・対象範囲・二次壁打ち条件)

# 確信度
1〜5(5最高)。理由1行。
"""

USER = """# 文脈
SES営業会社(2名)のCEO参謀AI「ジョブズ」が、gate_checker周辺の上限と
共謀リスク対策(複数モデル壁打ち)のコスト設計を再検討中。

# 既に確定した前提(変更不可)
- 論点A: フェーズ別モデル割振確定
  | フェーズ | モデル | 月回数 | 1回コスト |
  | research | gpt-5.4-mini | 5 | $0.006 |
  | requirements | gpt-5.4-mini | 15 | $0.006 |
  | design | gpt-5.4 | 8 | $0.043 |
  | pre_impl | gpt-5.4 | 15 | $0.020 |
  | implementation | gpt-5.3-codex | 30 | $0.056 |
  | test | gpt-5.4 | 30 | $0.013 |
  | final_gate | gpt-5.4 | 10 | $0.070 |
  合計 113回/月, $3.534/月
- 論点D: 安全装置4つ(Week1: 装置2+3 / Week2: 装置1 / Week3-4: 装置4)
- CostGuard: $8/日, $140/月 (上限固定)

# ジョブズの論点C提案

## (1) DAILY_CALL_LIMIT段階解放
| 段階 | 値 | 解放条件 | 1日上限コスト | CostGuard比 |
| 1 | 50 | 初期Week1 | $1.57 | 20% |
| 2 | 100 | Week2 装置1追加後 | $3.13 | 39% |
| 3 | 180 | Week3 装置4追加後 | $5.63 | 70% |
| 4 | 240 | 1ヶ月運用安定後 | $7.51 | 94% (最終天井) |
- 旧暫定300は廃止 (CostGuard超過のため)
- 平均単価 $0.0313/call で計算

## (2) DAILY_CALL_LIMIT対象範囲
- gate_checker系の壁打ちのみカウント
- mail_pipeline (nano $0.0003/call) と matching_v3 は別カウント
- 理由: 単価帯が桁違いで混ぜると閾値設計が破綻

## (3) 共謀リスク対策(二次壁打ち)発動条件
| フェーズ | 発動条件 | 月発動 | 追加コスト |
| design | 全件 | 8 | $0.34 |
| final_gate | ハイリスク判定時のみ | 3 | $0.21 |
| implementation | NG判定時のみ(月想定2回) | 2 | $0.11 |
追加 $0.66/月 → 総月コスト $3.94 + $0.66 = $4.60/月

# あなたの仕事
上記提案の盲点を探せ。特に注目すべき点:
- 「異常検知時のスパイク対応」として段階1=50は十分か / 過剰か
- 二次壁打ちの発動条件は運用で機械判定できるか
- CostGuard $8/日と DAILY_CALL_LIMIT の二重防御に意味があるか
- 月回数の前提が崩れる現実シナリオは何か(例: 大規模リファクタ月)

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
record(usage.prompt_tokens, usage.completion_tokens, MODEL, "sparring_daily_limit_critique")

print(f"\nUsed: {used}")
print(f"Content length: {len(result)}")
print("=" * 60)
print(result if result else "(EMPTY)")
print("=" * 60)
print(f"Actual cost: ${actual_cost:.4f} (in={usage.prompt_tokens}, out={usage.completion_tokens})")
print(f"Today total: ${daily_total():.4f}")

out_path = BASE / "gate_checker" / "results" / "daily_limit_critique.txt"
out_path.write_text(
    f"=== {MODEL} ({used}) ===\n"
    f"in={usage.prompt_tokens} out={usage.completion_tokens} cost=${actual_cost:.4f}\n\n"
    f"{result}\n",
    encoding="utf-8",
)
print(f"Saved: {out_path}")
