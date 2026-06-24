import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1メール処理あたりの平均トークン数を推定
# classify_email: subject+body(8000文字) + system(200) → 約2500 input / 100 output
# extract_affiliation: body(2000) + system(100) → 約600 input / 20 output
# ai_matching: project+engineers(JSON) → 約3000 input / 500 output
# double_check: 提案文+候補者 → 約2000 input / 800 output

CLAUDE_SONNET_IN = 3.0  # $3/1M tokens
CLAUDE_SONNET_OUT = 15.0  # $15/1M tokens
USD_JPY = 155

# 案件メール1件あたり（全ステップ）
project_in = 2500 + 600 + 3000 + 2000  # = 8100
project_out = 100 + 20 + 500 + 800  # = 1420
project_usd = (project_in / 1e6 * CLAUDE_SONNET_IN) + (project_out / 1e6 * CLAUDE_SONNET_OUT)
project_jpy = project_usd * USD_JPY

# 人材メール1件あたり（classify + affiliation + matching）
eng_in = 2500 + 600 + 1500
eng_out = 100 + 20 + 300
eng_usd = (eng_in / 1e6 * CLAUDE_SONNET_IN) + (eng_out / 1e6 * CLAUDE_SONNET_OUT)
eng_jpy = eng_usd * USD_JPY

# その他メール（classify only）
other_in = 2500
other_out = 100
other_usd = (other_in / 1e6 * CLAUDE_SONNET_IN) + (other_out / 1e6 * CLAUDE_SONNET_OUT)
other_jpy = other_usd * USD_JPY

print("=== 1メールあたりのコスト試算 ===")
print(f"案件メール: ${project_usd:.4f} / 約{project_jpy:.1f}円")
print(f"人材メール: ${eng_usd:.4f} / 約{eng_jpy:.1f}円")
print(f"その他(分類のみ): ${other_usd:.4f} / 約{other_jpy:.1f}円")
print()

# 1日の想定
# 共通: 2600件/日、松野: 71件/日（今後増える可能性）
# 割合: 案件20%、人材40%、その他40%（推定）
daily_total = 2671
ratio_project = 0.20
ratio_eng = 0.40
ratio_other = 0.40

daily_usd = (
    daily_total * ratio_project * project_usd
    + daily_total * ratio_eng * eng_usd
    + daily_total * ratio_other * other_usd
)
daily_jpy = daily_usd * USD_JPY

print("=== 1日あたりのコスト試算 ===")
print(f"処理件数: {daily_total}件/日")
print(f"  案件({ratio_project * 100:.0f}%): {daily_total * ratio_project:.0f}件")
print(f"  人材({ratio_eng * 100:.0f}%): {daily_total * ratio_eng:.0f}件")
print(f"  その他({ratio_other * 100:.0f}%): {daily_total * ratio_other:.0f}件")
print(f"合計: ${daily_usd:.2f}/日 / 約{daily_jpy:.0f}円/日")
print()

# 月換算
monthly_usd = daily_usd * 22  # 営業日22日
monthly_jpy = monthly_usd * USD_JPY
print("=== 月次コスト試算（営業日22日） ===")
print(f"合計: ${monthly_usd:.0f}/月 / 約{monthly_jpy:,.0f}円/月")
print()

# 改善案ごとの削減効果
print("=== 改善案別の削減効果 ===")

# A: 事前テキストフィルタ（SESキーワードなければclassify不要）
# SES関連キーワードあり率を60%とすると40%削減
filter_rate = 0.40
daily_filtered = daily_total * (1 - filter_rate)
daily_usd_a = (
    daily_filtered * ratio_project * project_usd
    + daily_filtered * ratio_eng * eng_usd
    + daily_filtered * ratio_other * other_usd
)
print("A: 事前テキストフィルタ（SESキーワード判定）")
print(f"   40%削減想定 → ${daily_usd_a * 22:.0f}/月 / 約{daily_usd_a * 22 * USD_JPY:,.0f}円/月")

# B: classify_emailをHaikuに変更（速い・安い）
HAIKU_IN = 0.8  # $0.8/1M
HAIKU_OUT = 4.0  # $4/1M
project_in_b = 2500 + 600
project_out_b = 100 + 20
# classifyとaffiliationはHaiku、matchingとdouble_checkはSonnet
project_usd_b = (
    (project_in_b / 1e6 * HAIKU_IN)
    + (project_out_b / 1e6 * HAIKU_OUT)
    + (5000 / 1e6 * CLAUDE_SONNET_IN)
    + (1300 / 1e6 * CLAUDE_SONNET_OUT)
)
daily_usd_b = (
    daily_total * ratio_project * project_usd_b
    + daily_total * ratio_eng * ((eng_in / 1e6 * HAIKU_IN) + (eng_out / 1e6 * HAIKU_OUT))
    + daily_total * ratio_other * ((other_in / 1e6 * HAIKU_IN) + (other_out / 1e6 * HAIKU_OUT))
)
print("B: 分類フェーズをHaikuに変更")
print(f"   → ${daily_usd_b * 22:.0f}/月 / 約{daily_usd_b * 22 * USD_JPY:,.0f}円/月")

# C: A+B複合
daily_usd_c = daily_usd_b * (1 - filter_rate)
print("C: A+B複合（フィルタ＋Haiku分類）")
print(f"   → ${daily_usd_c * 22:.0f}/月 / 約{daily_usd_c * 22 * USD_JPY:,.0f}円/月")

print()
print(f"現状維持: ${monthly_usd:.0f}/月 / 約{monthly_jpy:,.0f}円/月")
