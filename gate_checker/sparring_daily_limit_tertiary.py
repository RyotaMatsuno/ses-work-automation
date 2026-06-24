# -*- coding: utf-8 -*-
"""
Step3 RontenC: tertiary critique by GPT-5.5.
Target: jobz final-final plan (incorporates GPT-5.4 secondary critique).
Goal: find what GPT-5.4 missed; long-term / scaling perspective.
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
MAX_OUT = 6000
EST_COST = 4000 * PRICE_IN + MAX_OUT * PRICE_OUT

print(f"=== RontenC tertiary critique by {MODEL} ===")
print(f"Worst-case cost: ${EST_COST:.4f}")
print(f"Today total: ${daily_total():.4f}")

if not can_spend(EST_COST):
    print("[CostGuard] limit reached")
    sys.exit(1)

SYSTEM = """あなたは三次批判の専門カウンセラーです。
二次批判(GPT-5.4)が見落とした論点を探すのがあなたの仕事です。
GPT-5.4と同じ視点を繰り返してはいけません。

必ず以下の構造で応答:

# GPT-5.4が見落とした論点(3つ以上)
- <論点>: <なぜGPT-5.4は見落としたか> / <事業への影響>

# 長期視点での問題(法人化・スケール・人員増加観点)
- <問題>: <影響>

# 最終推奨(あなたの判断)
| 項目 | jobz案 | あなたの推奨 | 根拠 |

# 私が間違っている可能性
<1〜2行>

# 確信度
1〜5(5最高)。理由1行。
"""

USER = """# 経緯
SES営業会社(2名、CEO+業務委託)のCEO参謀AIが、gate_checker周辺の安全設計を再検討中。
一次批判(GPT-5.5)→ジョブズ折衷案→二次批判(GPT-5.4)→ジョブズ最終最終案、と来た。
あなたは三次批判者として、GPT-5.4が見落とした論点を探してください。

# 確定済み前提(変更不可)
- 論点A: フェーズ別モデル割振 確定 (合計113回/月, $3.94/月)
- 論点D: 安全装置4つの段階実装 (Week1: 装置2+3, Week2: 装置1, Week3-4: 装置4)
- CostGuard: $8/日, $140/月 (引き上げ前)

# GPT-5.4の二次批判の核心(これは既知)
- 平均単価固定でなくworst-case ($0.070/call) で計算すべき
- 段階4=240はCostGuard $8/日と重複(94%)、二重防御の意味なし
- 二次壁打ち「ハイリスク」「NG時」が機械判定不能
- implementation NG時のみは逆設計(危険な通過を取りこぼす)
- 一次/二次壁打ちの型番系列を変えて独立性確保
- 時限解放より実績連動解放

# ジョブズの最終最終案(あなたが批判する対象)

## (1) DAILY_CALL_LIMIT段階値
| 段階 | 値 | worst-case単価 | CostGuard比 |
| 1 | 30 | $2.10 | 26% |
| 2 | 60 | $4.20 | 53% |
| 3 | 90 | $6.30 | 79% |
| 4 | 110 | $7.70 | 96% |

## (2) 対象範囲(二層化)
- 層1: gate_checker系の回数上限(上記)
- 層2: AI全体の金額上限(CostGuard $8/日)

## (3) 二次壁打ち発動条件(機械判定可能)
- design: 全件
- final_gate: risk_score>=0.7 または 売上/契約/法務/freee/送信系タグ含有
- implementation: 差分>300行 または 権限/課金/認証/個人情報変更

## (4) 二次壁打ちモデル分離
- 一次: gpt-5.4 / gpt-5.3-codex
- 二次: gpt-5.4-mini

## (5) 解放条件
- 7日連続で「消費率<50%かつ装置1〜3警告0件」で次段階解放

# 月コスト試算
合計: $4.14/月 (CostGuard $140/月の3%)

# あなたの仕事
GPT-5.4と違う角度で批判せよ。特に注目:
- 長期(法人化後・人員増加後)に同じ設計が機能するか
- 「装置1〜3警告0件」を解放条件にする副作用(警告を抑える方向に運用が歪まないか)
- 二次壁打ちで mini を使うことで「品質チェッカーがチェッカー以下品質」になる構造的問題
- 「risk_score」をどうやって自動算出するか(これ自体が新モジュール必要)
- 二層化で「金額上限の早期到達でgate_checkerだけ止まる」運用不整合
- worst-case単価 $0.070 は本当に最悪値か(月末集中・障害対応で final_gate が連発する週末などの極値)
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
record(usage.prompt_tokens, usage.completion_tokens, MODEL, "sparring_daily_limit_tertiary")

print(f"\nUsed: {used}")
print(f"Content length: {len(result)}")
print("=" * 60)
print(result if result else "(EMPTY)")
print("=" * 60)
print(f"Actual cost: ${actual_cost:.4f} (in={usage.prompt_tokens}, out={usage.completion_tokens})")
print(f"Today total: ${daily_total():.4f}")

out_path = BASE / "gate_checker" / "results" / "daily_limit_tertiary.txt"
out_path.write_text(
    f"=== {MODEL} ({used}) ===\n"
    f"in={usage.prompt_tokens} out={usage.completion_tokens} cost=${actual_cost:.4f}\n\n"
    f"{result}\n",
    encoding="utf-8",
)
print(f"Saved: {out_path}")
