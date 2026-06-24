"""
Step A Phase②: 要件レビュー (o3-mini)
gate_checkerフェーズ別モデル対応改修の要件をo3-miniに検証させる
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

REQUIREMENTS = """
# 要件: gate_checker フェーズ別モデル切替対応

## 現状
- gate_checker/gate_check.py L38: REVIEW_MODEL = "gpt-4o" (一律)
- L42: PHASES = ("research", "requirements", "design", "pre_impl", "implementation", "test")
- L37: DAILY_CALL_LIMIT = 10 (1日10回上限)

## 改修内容
1. REVIEW_MODELを廃止、PHASE_MODELS辞書に置換:
   PHASE_MODELS = {
     "research":       "gpt-4o-mini",
     "requirements":   "o3-mini",
     "design":         "o3-mini",
     "pre_impl":       "gpt-4o-mini",
     "implementation": "gpt-4o",
     "test":           "gpt-4o",
     "final_gate":     "gpt-4o",
   }
2. PHASESに"final_gate"を追加
3. 引数--phaseがfinal_gateを受け付けるようにバリデーション拡張
4. APIcall時はphaseに応じてmodelを動的選択
5. o3-mini系はreasoning_effort="medium"を追加
6. cost計算のレートテーブルも更新(モデル別単価)

## 制約
- 既存の呼出インターフェース(--phase X --file Y)は変更しない
- CostGuard連携は維持
- 1コマンド=1API呼出のまま(無限ループ化しない)
- DAILY_CALL_LIMIT=10は据置(まずは検証期間)

## 完了条件
- python gate_check.py --phase requirements --file <任意>.md でo3-miniが動く
- python gate_check.py --phase final_gate --file <任意>.md でgpt-4oが動く
- daily_counter.jsonに記録される
- results/にJSON出力される

## レビュー観点
1. この要件で漏れはないか
2. 「o3-miniはreasoning_effortパラメータが必須」を見落としてないか
3. cost計算ロジックでminiとo3系の単価差を吸収できるか
4. PHASES変更時の後方互換性
5. 「DAILY_CALL_LIMIT=10は据置」で1日240回想定とのギャップは問題か
"""

PROMPT = f"""
あなたは厳密なシステム要件レビュアー。以下の要件を批判的にレビューせよ。
{REQUIREMENTS}

出力形式:
## 要件の致命的問題(あれば)
## 見落とし
## 改修後のリスク
## GO/HOLD/NG判定
## 必須修正事項
"""

print("=" * 60)
print("Step A Phase②: 要件レビュー (o3-mini)")
print("=" * 60)

response = client.chat.completions.create(
    model="o3-mini",
    messages=[{"role": "user", "content": PROMPT}],
    reasoning_effort="medium",
)

result = response.choices[0].message.content
print(result)
print()
print(f"トークン: in={response.usage.prompt_tokens} / out={response.usage.completion_tokens}")
cost = response.usage.prompt_tokens * 1.1 / 1_000_000 + response.usage.completion_tokens * 4.4 / 1_000_000
print(f"コスト: ${cost:.4f}")
