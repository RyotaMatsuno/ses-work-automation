import json

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\poc_engineers.json", "r", encoding="utf-8") as f:
    engineers = json.load(f)
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\poc_projects.json", "r", encoding="utf-8") as f:
    projects = json.load(f)

# === 対策1: スキルなし案件の本文からキーワード自動抽出 ===
TECH_KEYWORDS = [
    "java",
    "python",
    "c#",
    "php",
    "ruby",
    "go",
    "rust",
    "kotlin",
    "swift",
    "scala",
    "javascript",
    "typescript",
    "react",
    "vue",
    "angular",
    "node.js",
    "next.js",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "oracle",
    "mysql",
    "postgresql",
    "mongodb",
    "redis",
    "sql server",
    "linux",
    "windows server",
    "vmware",
    "cisco",
    "network",
    "spring",
    "django",
    "flask",
    "laravel",
    ".net",
    "pmo",
    "pmp",
    "itil",
    "agile",
    "scrum",
    "sap",
    "salesforce",
    "servicenow",
    "terraform",
    "ansible",
    "jenkins",
    "ci/cd",
    "git",
    "html",
    "css",
]


def extract_skills_from_text(text):
    text_lower = text.lower()
    found = set()
    for kw in TECH_KEYWORDS:
        if kw in text_lower:
            found.add(kw)
    return found


# === 対策2: 「全必須スキル一致」フィルタに変更 ===
results_all_match = []
results_any_match = []

for p in projects:
    p_skills = set(s.strip().lower() for s in p["skills"].split(",") if s.strip())

    # スキルなしの場合、本文からキーワード抽出
    if not p_skills and p["detail"]:
        p_skills = extract_skills_from_text(p["detail"] + " " + p["name"])

    if not p_skills:
        results_all_match.append(len(engineers))
        results_any_match.append(len(engineers))
        continue

    all_count = 0
    any_count = 0
    for e in engineers:
        e_skills = set(s.strip().lower() for s in e["skills"].split(",") if s.strip())
        if p_skills & e_skills:
            any_count += 1
        if p_skills <= e_skills:  # 全必須スキルが含まれている
            all_count += 1

    results_all_match.append(all_count)
    results_any_match.append(any_count)

import numpy as np

# スキルなし→本文抽出後のスキル有無
extracted_count = 0
still_no_skill = 0
for p in projects:
    p_skills = set(s.strip().lower() for s in p["skills"].split(",") if s.strip())
    if not p_skills:
        extracted = extract_skills_from_text(p["detail"] + " " + p["name"])
        if extracted:
            extracted_count += 1
        else:
            still_no_skill += 1

print("=== 本文からのスキル自動抽出結果 ===")
print("元々スキルタグなし: 44件")
print(f"  本文から抽出成功: {extracted_count}件")
print(f"  それでもスキルなし: {still_no_skill}件")

print("\n=== フィルタ方式比較 ===")
any_arr = np.array(results_any_match)
all_arr = np.array(results_all_match)

print(f"「1つでも一致」: 平均{np.mean(any_arr):.1f}人, 合計{np.sum(any_arr)}回")
print(f"「全必須一致」:  平均{np.mean(all_arr):.1f}人, 合計{np.sum(all_arr)}回")

# 全必須一致の分布
print("\n=== 「全必須一致」の分布 ===")
for threshold in [0, 1, 3, 5, 10, 20]:
    pct = np.sum(all_arr <= threshold) / len(all_arr) * 100
    print(f"  {threshold}人以下: {pct:.0f}% ({np.sum(all_arr <= threshold)}件)")

# 0人マッチの案件
zero_match = np.sum(all_arr == 0)
print(f"\n0人マッチ案件: {zero_match}件")

# 1日1,114件に外挿
scale = 1114 / len(projects)

# still_no_skill案件は全員チェック、それ以外は全必須一致のみ
total_all = np.sum(all_arr)
daily_all = total_all * scale

print("\n=== 1日1,114件コストシミュレーション（全必須一致+本文抽出） ===")
print(f"1日のLLM呼び出し: {daily_all:.0f}回")
for name, cost in [
    ("Nova Micro", 0.000372),
    ("Nova Micro Batch", 0.000186),
    ("Gemini FL", 0.001062),
    ("Gemini FL Batch", 0.000531),
]:
    daily = daily_all * cost
    monthly = daily * 30
    print(f"  {name}: ${daily:.2f}/日 → 月${monthly:.0f} / 約{monthly * 155:,.0f}円")
