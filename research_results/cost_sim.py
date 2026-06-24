import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=== 全経路コスト試算 ===")
print()

haiku_cost = 0.002  # 1コールあたり$0.002
project_rate = 0.20  # 分類結果のうち案件は約20%（今日: 30/150=20%）
matching_calls_per_project = 3  # 案件1件あたりマッチングLLM呼び出し

print(f"前提: 分類1回=${haiku_cost}")
print(f"  案件率={project_rate*100:.0f}%（実績ベース）")
print(f"  案件1件あたりマッチング{matching_calls_per_project}コール")
print()

scenarios = [
    ("通常日（新着100件）", 100),
    ("多い日（新着300件）", 300),
    ("平日ピーク（500件）", 500),
    ("バックログ消化（743件/日）", 743),
    ("PROCESS無制限 x 13回/日（最大2600件）", 2600),
]

for name, daily in scenarios:
    classify = daily * haiku_cost
    projects = int(daily * project_rate)
    match_cost = projects * matching_calls_per_project * haiku_cost
    total = classify + match_cost
    monthly = total * 22

    daily_ok = "OK" if total < 8 else "NG"
    monthly_ok = "OK" if monthly < 140 else "NG"

    print(f"--- {name} ---")
    print(f"  分類: {daily}コール = ${classify:.2f}")
    print(f"  案件{projects}件 x {matching_calls_per_project}コール = ${match_cost:.2f}")
    print(f"  日次合計: ${total:.2f} / $8制限 -> {daily_ok}")
    print(f"  月次: ${monthly:.2f} / $140制限 -> {monthly_ok}")
    print()

# 6月残り予算
remaining_budget = 140 - 0.55
remaining_days = 30 - 19  # 6/20-6/30 = 11日
daily_budget = remaining_budget / remaining_days
print(f"=== 6月残り予算 ===")
print(f"  残り: ${remaining_budget:.2f} / {remaining_days}日")
print(f"  1日あたり使える額: ${daily_budget:.2f}")
