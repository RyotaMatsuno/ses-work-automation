import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Haiku 4.5の実際の単価（GPT回答より）
HAIKU_IN = 0.50 / 1e6  # $0.5/1Mtokens（私の試算は0.8だった）
HAIKU_OUT = 2.50 / 1e6  # $2.5/1Mtokens（私の試算は4.0だった）
USD_JPY = 155

DAILY_TOTAL = 2700
skip_count = DAILY_TOTAL * 0.130  # 351件
attach_count = DAILY_TOTAL * 0.266  # 718件
project_count = DAILY_TOTAL * 0.139  # 375件
engineer_count = DAILY_TOTAL * 0.220  # 594件
unknown_count = DAILY_TOTAL * 0.246  # 664件

# ② 添付人材抽出
attach_cost = attach_count * (400 * HAIKU_IN + 150 * HAIKU_OUT)
# ③ 案件抽出
project_cost = project_count * (500 * HAIKU_IN + 200 * HAIKU_OUT)
# ④ 人材抽出
engineer_cost = engineer_count * (400 * HAIKU_IN + 150 * HAIKU_OUT)
# ⑤ unknown分類
unknown_cost = unknown_count * (200 * HAIKU_IN + 30 * HAIKU_OUT)
# ⑤ unknown有効分抽出（50%が案件・人材）
unknown_valid = unknown_count * 0.5 * (450 * HAIKU_IN + 175 * HAIKU_OUT)
# マッチング（ルール絞り3件×Haiku）
matching_cost = project_count * 3 * (600 * HAIKU_IN + 300 * HAIKU_OUT)

daily_usd = attach_cost + project_cost + engineer_cost + unknown_cost + unknown_valid + matching_cost
monthly_usd = daily_usd * 22
monthly_batch = monthly_usd * 0.5  # Batch API 50%割引

print("=== Haiku 4.5実際単価での再試算 ===")
print("私の試算時: Haiku in=$0.80/M out=$4.00/M")
print("実際の単価: Haiku in=$0.50/M out=$2.50/M（約37%安い）")
print()
print(f"合計: ${daily_usd:.4f}/日")
print(f"月次（22日）通常API: ${monthly_usd:.2f} / 約{monthly_usd * USD_JPY:,.0f}円")
print(f"月次（22日）Batch API: ${monthly_batch:.2f} / 約{monthly_batch * USD_JPY:,.0f}円")
print()
print("現状比: $1,220/月 →")
print(f"  通常API:  ${monthly_usd:.1f}/月（{(1 - monthly_usd / 1220) * 100:.0f}%削減）")
print(f"  Batch API: ${monthly_batch:.1f}/月（{(1 - monthly_batch / 1220) * 100:.0f}%削減）")
