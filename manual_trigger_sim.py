# 手動トリガー型のコスト試算
cost_per_call = 0.0094
rate = 155  # 円/ドル

# 実績値
engineers = 143
projects_2days = 3767
no_skill_rate = 0.52  # スキルタグなし52%
skill_match_rate = 0.314  # スキルあり案件のうち一致率31.4%

# スキルフィルタ後の案件数（1人あたり）
projects_with_skill = int(projects_2days * (1 - no_skill_rate))  # 1816件
matched_per_engineer = int(projects_with_skill * skill_match_rate)  # スキル一致

print(f"2日以内の案件: {projects_2days}件")
print(f"  うちスキルタグあり: {projects_with_skill}件")
print(f"  スキル一致（平均/人）: {matched_per_engineer}件")

print("\n=== 手動トリガー型コスト試算 ===")
print("（1人分マッチング = スキル一致案件のみAI判定）")
print()

cost_per_person = matched_per_engineer * cost_per_call
print(
    f"1回のマッチング（1人分）: {matched_per_engineer}件 × ${cost_per_call} = ${cost_per_person:.2f} / 約{cost_per_person * rate:.0f}円"
)
print()

for times_per_month in [10, 20, 30, 50]:
    monthly = cost_per_person * times_per_month
    print(f"月{times_per_month}回実行: ${monthly:.2f} / 約{monthly * rate:,.0f}円")
