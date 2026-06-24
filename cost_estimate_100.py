# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 現状の実測値から試算
# sessales: 今日4,454件 / matsuno: 114件 / okamoto: 13件
# 合計 約4,580件/日

# mail_pipelineの実測コスト
# 今日: $2.83 / 16回実行 / 合計処理約200件×16=3,200件取得（重複含む）
# → 実際に新規分類したのは279件登録+191スキップ+181NG ≈ 651件
# → 651件で$2.83 → 1件あたり$0.00435

cost_per_mail = 2.83 / 651
print(f"1通あたりコスト（実測）: ${cost_per_mail:.5f}")

# 1日の想定メール数
daily_total = 4580  # sessales4454 + matsuno114 + okamoto13

# ただしキーワードフィルタで除外できる非案件メールを差し引く
# スキップ191件の内訳: 請求書・注文書・勤務表等（全体の約29%）
# → 実際の案件・人材メールは約70%と仮定
effective_rate = 0.70
effective_mails = int(daily_total * effective_rate)
print(f"有効メール数（非案件除外後）: 約{effective_mails}件/日")

# 日次コスト試算
daily_cost = effective_mails * cost_per_mail
monthly_cost = daily_cost * 22  # 平日22日
print("\n100%処理した場合:")
print(f"  日次コスト: ${daily_cost:.2f}/日")
print(f"  月次コスト: ${monthly_cost:.2f}/月（平日22日）")

# 月$100予算でいける件数
budget_monthly = 100
budget_daily = budget_monthly / 22
max_mails_per_day = budget_daily / cost_per_mail
print("\n月$100予算の場合:")
print(f"  日次予算: ${budget_daily:.2f}/日")
print(f"  処理可能件数: {max_mails_per_day:.0f}件/日")
print(f"  カバー率: {max_mails_per_day / daily_total * 100:.0f}%")

# max_tokensを8000に修正済みなので、LLM失敗が減りコストが変わる可能性
# 今日はmax_tokens 4000の失敗分(181件)が再処理対象に残った → 明日から改善
# 実際のLLM分類成功件数 = 279+191 = 470件 → $2.83
corrected_cost = 2.83 / 470
print("\n修正後の推定（LLM失敗除く）:")
print(f"  1通あたりコスト: ${corrected_cost:.5f}")
daily_cost2 = effective_mails * corrected_cost
monthly_cost2 = daily_cost2 * 22
print(f"  月次コスト（100%処理）: ${monthly_cost2:.2f}/月")
print(
    f"  月$100で処理可能: {(100 / 22 / corrected_cost):.0f}件/日 → カバー率{(100 / 22 / corrected_cost) / daily_total * 100:.0f}%"
)
