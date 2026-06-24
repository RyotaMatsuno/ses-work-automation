import json

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\poc_engineers.json", "r", encoding="utf-8") as f:
    engineers = json.load(f)
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\poc_projects.json", "r", encoding="utf-8") as f:
    projects = json.load(f)

# 案件ごとに「スキルタグが1つでも一致するエンジニア数」を計算
match_counts = []
no_skill_count = 0

for p in projects:
    p_skills = set(s.strip().lower() for s in p["skills"].split(",") if s.strip())
    if not p_skills:
        no_skill_count += 1
        match_counts.append(len(engineers))  # スキルなし案件は全員対象
        continue

    matched = 0
    for e in engineers:
        e_skills = set(s.strip().lower() for s in e["skills"].split(",") if s.strip())
        if p_skills & e_skills:
            matched += 1
    match_counts.append(matched)

import numpy as np

arr = np.array(match_counts)
print(f"案件数: {len(projects)}")
print(f"スキルタグなし案件: {no_skill_count}件")
print(f"スキルタグあり案件: {len(projects) - no_skill_count}件")
print("\nスキルマッチ人数（スキルあり案件のみ）:")
skill_arr = np.array([c for c, p in zip(match_counts, projects) if p["skills"].strip()])
print(f"  平均: {np.mean(skill_arr):.1f}人")
print(f"  中央: {np.median(skill_arr):.1f}人")
print(f"  最小: {np.min(skill_arr)}人")
print(f"  最大: {np.max(skill_arr)}人")

# 分布
for threshold in [5, 10, 15, 20, 30, 50]:
    pct = np.sum(skill_arr <= threshold) / len(skill_arr) * 100
    print(f"  {threshold}人以下の案件: {pct:.0f}%")

# スキルなし案件の案件詳細を見る
print("\n=== スキルなし案件のdetail有無 ===")
no_skill_detail = 0
for p in projects:
    if not p["skills"].strip():
        if p["detail"].strip():
            no_skill_detail += 1
print(f"スキルなし案件: {no_skill_count}件中、detail（本文）あり: {no_skill_detail}件")

# トータル呼び出し回数のシミュレーション
total_with_skill = sum(c for c, p in zip(match_counts, projects) if p["skills"].strip())
total_no_skill = no_skill_count * len(engineers)
total = total_with_skill + total_no_skill
print("\n=== ルールベースフィルタ後のLLM呼び出し回数（100案件） ===")
print(f"スキルあり案件: {total_with_skill}回")
print(f"スキルなし案件: {total_no_skill}回")
print(
    f"合計: {total}回 (全組み合わせ{len(projects) * len(engineers)}回からの削減率: {(1 - total / (len(projects) * len(engineers))) * 100:.1f}%)"
)

# 1日1,114件に外挿
scale = 1114 / len(projects)
daily_calls = total * scale
print("\n=== 1日1,114件に外挿 ===")
print(f"1日のLLM呼び出し: {daily_calls:.0f}回")
for name, cost in [
    ("Nova Micro", 0.000186),
    ("Nova Micro Batch", 0.0000932),
    ("Gemini Flash-Lite", 0.000531),
    ("Gemini Flash-Lite Batch", 0.000266),
]:
    daily = daily_calls * cost
    monthly = daily * 30
    print(f"  {name}: ${daily:.2f}/日 → 月${monthly:.0f} / 約{monthly * 155:,.0f}円")
