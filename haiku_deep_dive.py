daily_unique = 1114
retry_rate = 1.10
safety_margin = 1.15
daily_calls = daily_unique * retry_rate * safety_margin
haiku_cost_per_call = 2300 * 1.00 / 1e6 + 300 * 5.00 / 1e6  # $0.0038

print(f"1日の呼び出し: {daily_calls:.0f}回")
print(f"Haiku 1回: ${haiku_cost_per_call:.4f}")
print()

for days, label in [(20, "20営業日"), (22, "22営業日"), (25, "25営業日"), (30, "30日")]:
    monthly = daily_calls * days * haiku_cost_per_call
    margin = 150 - monthly
    flag = "OK" if monthly <= 150 else "OVER"
    print(f"  {label}: ${monthly:.1f} / {monthly * 155:,.0f}円 (残り${margin:.0f}) [{flag}]")

# コスト上限から逆算: 1日何回まで呼べるか
print()
print("=== 逆算: $150以内に収めるための1日上限 ===")
for days in [20, 22, 25]:
    max_daily = 150 / days / haiku_cost_per_call
    print(f"  {days}営業日: 1日{max_daily:.0f}回まで（案件{max_daily / retry_rate / safety_margin:.0f}件/日まで安全）")
