import json

import numpy as np

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\poc_engineers.json", "r", encoding="utf-8") as f:
    engineers = json.load(f)
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\poc_projects.json", "r", encoding="utf-8") as f:
    projects = json.load(f)

# === 新設計: エンジニア起点バッチプロンプト ===
# 1回のAPI呼び出しで「このエンジニアに合う案件はどれ？」を30件ずつ判定
# プロンプトを案件スキル+単価のみに圧縮

# トークン数の見積もり
# エンジニア情報: スキル列挙+単価 ≒ 150tok
# 案件1件: "1. Java/Spring/AWS, 65万" ≒ 30tok
# 30件分: 30 × 30 = 900tok
# システムプロンプト: 200tok
# 合計入力: 1,250tok
# 出力: マッチ番号リスト ≒ 50tok

INPUT_PER_BATCH = 1250
OUTPUT_PER_BATCH = 50
BATCH_SIZE = 30  # 1回に判定する案件数

# 料金（通常API / Batch API）
models = {
    "Nova Micro": (0.035, 0.14),
    "Nova Micro Batch": (0.0175, 0.07),
    "Gemini FL-Lite": (0.10, 0.40),
    "Gemini FL-Lite Batch": (0.05, 0.20),
    "GPT-4.1-nano": (0.10, 0.40),
    "GPT-4.1-nano Batch": (0.05, 0.20),
    "Claude Haiku（現行参考）": (1.00, 5.00),
}

# 1日の案件数
daily_projects = 1114
# エンジニア数
num_engineers = 154

# エンジニア1人あたりの呼び出し回数
calls_per_engineer = int(np.ceil(daily_projects / BATCH_SIZE))

# 全エンジニア分
daily_calls = num_engineers * calls_per_engineer

print("=" * 70)
print("=== 新設計: バッチプロンプト（30案件/回） ===")
print("=" * 70)
print(f"1日の案件数: {daily_projects}件")
print(f"エンジニア: {num_engineers}人")
print(f"1人あたりの呼び出し: ceil({daily_projects}/{BATCH_SIZE}) = {calls_per_engineer}回")
print(f"1日の合計呼び出し: {num_engineers} × {calls_per_engineer} = {daily_calls}回")
print(f"入力tok/回: {INPUT_PER_BATCH}, 出力tok/回: {OUTPUT_PER_BATCH}")
print()

for name, (in_price, out_price) in models.items():
    cost_per_call = INPUT_PER_BATCH * in_price / 1_000_000 + OUTPUT_PER_BATCH * out_price / 1_000_000
    daily_cost = daily_calls * cost_per_call
    monthly_cost = daily_cost * 30
    ok = "✅" if monthly_cost <= 150 else "❌"
    print(
        f"  {name:30s}: ${cost_per_call:.7f}/回 → ${daily_cost:.2f}/日 → 月${monthly_cost:.1f} / {monthly_cost * 155:,.0f}円 {ok}"
    )

# ルールフィルタ併用版（スキル1つ以上一致のみLLMに投げる）
print()
print("=" * 70)
print("=== ルールフィルタ + バッチプロンプト（スキル一致案件のみ） ===")
print("=" * 70)

# 実測: スキル一致率49.6/154 = 32.2%（スキルあり案件の場合）
# スキルなし+本文抽出失敗案件23%は全件
skill_match_rate = 0.322
no_skill_rate = 0.23  # スキルタグも本文抽出もなし

# スキルあり案件は平均49.6人/案件
avg_matched_per_project = 49.6

# エンジニア起点で考える: 1人あたり何件の案件がマッチするか
# スキルあり案件1,114 × 77% = 858件のうち、1人あたりスキル一致は858×32.2% = 276件
# スキルなし案件1,114 × 23% = 256件は全件
# 1人あたり: 276 + 256 = 532件
# バッチ30件/回 → ceil(532/30) = 18回/人
# 全体: 154人 × 18回 = 2,772回/日

matched_per_engineer_skill = int(daily_projects * 0.77 * skill_match_rate)
matched_per_engineer_noskill = int(daily_projects * no_skill_rate)
matched_per_engineer = matched_per_engineer_skill + matched_per_engineer_noskill
calls_filtered = num_engineers * int(np.ceil(matched_per_engineer / BATCH_SIZE))

print(
    f"1人あたりマッチ案件: {matched_per_engineer_skill}(スキル一致) + {matched_per_engineer_noskill}(スキルなし) = {matched_per_engineer}件"
)
print(
    f"1人あたり呼び出し: ceil({matched_per_engineer}/{BATCH_SIZE}) = {int(np.ceil(matched_per_engineer / BATCH_SIZE))}回"
)
print(f"1日の合計呼び出し: {calls_filtered}回")
print()

for name, (in_price, out_price) in models.items():
    cost_per_call = INPUT_PER_BATCH * in_price / 1_000_000 + OUTPUT_PER_BATCH * out_price / 1_000_000
    daily_cost = calls_filtered * cost_per_call
    monthly_cost = daily_cost * 30
    ok = "✅" if monthly_cost <= 150 else "❌"
    print(f"  {name:30s}: ${daily_cost:.2f}/日 → 月${monthly_cost:.1f} / {monthly_cost * 155:,.0f}円 {ok}")
