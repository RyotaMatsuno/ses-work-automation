# -*- coding: utf-8 -*-
"""PROCESS_LIMIT 10→25 に変更 + 取り込み見通し計算"""

import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

pp = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"

# 1. 変更前確認
with open(pp, "r", encoding="utf-8") as f:
    content = f.read()

# 現在値確認
for m in re.finditer(r"^(FETCH_LIMIT|PROCESS_LIMIT|DAILY_COST_LIMIT_USD)\s*=.*$", content, re.MULTILINE):
    print(f"  BEFORE: {m.group()}")

# 2. PROCESS_LIMIT=10→25 に変更
content_new = re.sub(
    r"^(PROCESS_LIMIT\s*=\s*)10(\s*#.*)$",
    r"\g<1>25  # [2026-06-18] 10→25 段階復旧（4連続OK前提で次回50へ）",
    content,
    flags=re.MULTILINE,
)

# FETCH_LIMITも50→100に上げる（取得側がボトルネックにならないよう）
content_new = re.sub(
    r"^(FETCH_LIMIT\s*=\s*)50(\s*#.*)$", r"\g<1>100  # [2026-06-18] 50→100 段階復旧", content_new, flags=re.MULTILINE
)

with open(pp, "w", encoding="utf-8") as f:
    f.write(content_new)

# 3. 変更後確認
with open(pp, "r", encoding="utf-8") as f:
    for line in f:
        if re.match(r"^(FETCH_LIMIT|PROCESS_LIMIT|DAILY_COST_LIMIT_USD)\s*=", line):
            print(f"  AFTER: {line.strip()}")

print("\n=== 取り込み見通し計算 ===")
# 通常稼働時の実績: FETCH=200/PROCESS=50 で 26-31件/日がNotion登録
# → 1回あたり平均 26/17 ≒ 1.5件が「案件」判定
# → LLMに投げる「新規メール」は1回あたり10-50件だが、案件判定されるのは少数

# PROCESS=25, FETCH=100 の場合
fetch = 100
process = 25
runs_per_day = 17  # 7:00-23:00 hourly

print(f"  FETCH_LIMIT: {fetch} (×3アカウント = {fetch * 3}件/回 取得)")
print(f"  PROCESS_LIMIT: {process} (新規メール{process}件/回 LLM処理)")
print(f"  実行回数: {runs_per_day}回/日")
print(f"  LLM処理能力: {process * runs_per_day}件/日")
print()
print("  通常時の実績（FETCH=200/PROCESS=50時）:")
print("    Notion登録: 26-31件/日")
print("    → 1回あたり約1.5-1.8件が「案件」判定")
print()
print("  PROCESS=25/FETCH=100 の見通し:")
print(f"    LLM処理能力: {process * runs_per_day}件/日（十分）")
print("    FETCH=100 → sessales 1時間243件中100件カバー（約41%）")
print("    FETCH=200 → sessales 1時間243件中200件カバー（約82%）")
print()
print("  ★ボトルネックはPROCESSではなくFETCH側")
print("    FETCH=100: 1時間に来るメールの41%を見れる")
print("    FETCH=200(最終目標): 82%カバー")
print("    ただし「案件メール」は全体の一部なので、実際のNotion登録は概ね拾える")
