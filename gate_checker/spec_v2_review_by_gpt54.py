# -*- coding: utf-8 -*-
"""SPEC.md v2.0 を gpt-5.4 で直接レビューする。
gate_checker.gate_check.py が GPT-4o のハルシネーション
(レビュー対象を読まずに既知パターンで生成) を起こしたため、別経路で実施。
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
MAX_OUT = 12000

spec_path = BASE / "gate_checker" / "SPEC.md"
claude_path = BASE / "gate_checker" / "CLAUDE.md"
tasks_path = BASE / "gate_checker" / "TASKS.md"

spec_text = spec_path.read_text(encoding="utf-8")
claude_text = claude_path.read_text(encoding="utf-8")
tasks_text = tasks_path.read_text(encoding="utf-8")

est_in = (len(spec_text) + len(claude_text) + len(tasks_text)) // 3 + 1000
est_cost = est_in * PRICE_IN + MAX_OUT * PRICE_OUT
print(f"=== gate_checker v2.0 SPEC review by {MODEL} ===")
print(f"Worst-case cost: ${est_cost:.4f}")
print(f"Today total: ${daily_total():.4f}")

if not can_spend(est_in, MAX_OUT, MODEL):
    print("[CostGuard] limit reached")
    sys.exit(1)

SYSTEM = """あなたはSES業界の経営参謀向けに開発SPEC.mdをレビューする専門家です。
レビュー対象は実在のSPEC.mdです。必ずSPEC.md本文を読んでから論評してください。
ハルシネーション(既知パターンで埋める)は禁止です。SPEC.md本文に出てくる固有名詞・数字・関数名を必ず1つ以上引用してください。

レビュー観点:
1. SPECとTASKS、CLAUDE.mdとの整合性(矛盾・抜け)
2. 仕様の論理的破綻(矛盾・循環参照・不可能な要件)
3. CostGuard被覆漏れ
4. 通知集中による事故リスク(LINE月200通枠)
5. 装置2・装置3の発動条件は適切か(過敏/鈍感)
6. フェーズ別モデル名の妥当性(gpt-5.4-nano/gpt-5.3-codex等が実在するか不安あり、SPEC側で対応してあるか)
7. exit code変更(1→2)による既存呼び出し側の互換性
8. agreement_checkerを触らないとした選択の妥当性
9. 単価表(MODEL_PRICING)の検証手順は明記されているか
10. テスト方針の網羅性

出力フォーマット末尾:
【判定: GO】 / 【判定: 条件付きGO】 / 【判定: NG】

判定の前に、SPEC.md本文から固有名詞・数字を3つ以上引用し、それに対するコメントを書いてください。
"""

USER = f"""# レビュー対象: gate_checker SPEC.md v2.0 + CLAUDE.md + TASKS.md

## SPEC.md (本文)

{spec_text}

---

## CLAUDE.md (本文)

{claude_text}

---

## TASKS.md (本文)

{tasks_text}

---

# 指示
上記3点セット v2.0 を、SES営業自動化システムの開発SPECレビューとして精査せよ。
特に「Week1スコープに収まっているか」「v1.0との後方互換が保たれているか」「装置2と装置3の発動条件・通知設計に事故リスクはないか」を重点的に見よ。

判定前に必ずSPEC.md本文から固有名詞(関数名/定数名/モデル名/コスト数値)を3つ以上引用してコメントすること。
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

result = response.choices[0].message.content or ""
usage = response.usage
actual_cost = usage.prompt_tokens * PRICE_IN + usage.completion_tokens * PRICE_OUT
record(usage.prompt_tokens, usage.completion_tokens, MODEL, "spec_v2_review_by_gpt54")

print(f"\nContent length: {len(result)}")
print("=" * 60)
print(result if result else "(EMPTY)")
print("=" * 60)
print(f"Actual cost: ${actual_cost:.4f} (in={usage.prompt_tokens}, out={usage.completion_tokens})")
print(f"Today total: ${daily_total():.4f}")

out_path = BASE / "gate_checker" / "results" / "spec_v2_review_by_gpt54.txt"
out_path.write_text(
    f"=== gate_checker v2.0 SPEC review by {MODEL} ===\n"
    f"in={usage.prompt_tokens} out={usage.completion_tokens} cost=${actual_cost:.4f}\n\n"
    f"{result}\n",
    encoding="utf-8",
)
print(f"Saved: {out_path}")
