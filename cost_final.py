
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 実測値
DAILY_TOTAL   = 2700
ATTACH_RATE   = 0.266   # 添付あり=人材確定（実測26.6%）
RULE_PROJECT  = 0.139   # ルールで案件確定
RULE_ENGINEER = 0.485   # ルールで人材確定（添付含む）
RULE_SKIP     = 0.130   # ルールでスキップ
UNKNOWN_RATE  = 0.246   # Haiku分類が必要な残り

# ただし添付ありは既にengineerに含まれているので整理
# 実際の処理フロー別件数
skip_count    = DAILY_TOTAL * RULE_SKIP                         # 351件 コスト0
project_count = DAILY_TOTAL * RULE_PROJECT                      # 375件
engineer_count= DAILY_TOTAL * (RULE_ENGINEER - ATTACH_RATE)    # 593件（添付なし人材）
attach_count  = DAILY_TOTAL * ATTACH_RATE                      # 718件（添付あり→人材確定）
unknown_count = DAILY_TOTAL * UNKNOWN_RATE                      # 664件

print("=== 処理フロー別件数（1日2700件） ===")
print(f"① skipルール除外:        {skip_count:.0f}件 → コスト0")
print(f"② 添付あり→人材確定:    {attach_count:.0f}件 → Haiku抽出のみ")
print(f"③ 案件ルール確定:        {project_count:.0f}件 → Haiku構造化抽出")
print(f"④ 人材ルール確定(添付なし): {engineer_count:.0f}件 → Haiku構造化抽出")
print(f"⑤ unknown→Haiku分類:    {unknown_count:.0f}件 → Haiku判定")
print()

HAIKU_IN  = 0.8  / 1e6   # $0.8/1Mtokens
HAIKU_OUT = 4.0  / 1e6   # $4/1Mtokens
USD_JPY   = 155

# ② 添付あり人材: スキルシート抽出（Haiku） 件名+冒頭200文字で名前・スキル抽出
# Drive保存はAPI費用なし
attach_cost = attach_count * (
    (400 * HAIKU_IN) + (150 * HAIKU_OUT)   # 抽出: 400in/150out
)

# ③ 案件: 本文200文字で構造化抽出（案件名・スキル・単価・勤務地）
project_cost = project_count * (
    (500 * HAIKU_IN) + (200 * HAIKU_OUT)   # 抽出: 500in/200out
)

# ④ 人材（添付なし）: 本文200文字で構造化抽出
engineer_cost = engineer_count * (
    (400 * HAIKU_IN) + (150 * HAIKU_OUT)   # 抽出: 400in/150out
)

# ⑤ unknown分類: 件名+冒頭100文字でHaiku分類
unknown_cost = unknown_count * (
    (200 * HAIKU_IN) + (30 * HAIKU_OUT)    # 分類: 200in/30out
)
# unknownのうち案件・人材になったものの抽出コスト（50%が有効と仮定）
unknown_valid_cost = unknown_count * 0.5 * (
    (450 * HAIKU_IN) + (175 * HAIKU_OUT)
)

daily_usd = attach_cost + project_cost + engineer_cost + unknown_cost + unknown_valid_cost
monthly_usd = daily_usd * 22

print("=== コスト内訳（1日） ===")
print(f"② 添付あり人材抽出:   ${attach_cost:.4f}")
print(f"③ 案件構造化抽出:     ${project_cost:.4f}")
print(f"④ 人材構造化抽出:     ${engineer_cost:.4f}")
print(f"⑤ unknown Haiku分類:  ${unknown_cost:.4f}")
print(f"⑤ unknown 有効分抽出: ${unknown_valid_cost:.4f}")
print(f"合計:                  ${daily_usd:.4f}/日 / 約{daily_usd*USD_JPY:.0f}円/日")
print()
print(f"=== 月次コスト（22営業日） ===")
print(f"${monthly_usd:.2f}/月 / 約{monthly_usd*USD_JPY:,.0f}円/月")
print()

# マッチング処理は別途（案件・人材の登録後に一括バッチ）
# 案件×人材マッチング: 1案件あたり30人材と照合 → Haiku
# 1日の新規案件375件、1案件10候補まで
matching_daily = project_count * 10 * (600 * HAIKU_IN + 300 * HAIKU_OUT)
matching_monthly = matching_daily * 22
print(f"=== マッチング処理（別途） ===")
print(f"${matching_daily:.4f}/日 / 月${matching_monthly:.2f} / 約{matching_monthly*USD_JPY:,.0f}円/月")
print()

total_monthly = monthly_usd + matching_monthly
print(f"=== 合計月次コスト ===")
print(f"メール処理:   ${monthly_usd:.2f}")
print(f"マッチング:   ${matching_monthly:.2f}")
print(f"合計:         ${total_monthly:.2f}/月 / 約{total_monthly*USD_JPY:,.0f}円/月")
print()
print(f"現状比: $1,220/月 → ${total_monthly:.1f}/月")
print(f"削減率: {(1-total_monthly/1220)*100:.0f}%削減")
