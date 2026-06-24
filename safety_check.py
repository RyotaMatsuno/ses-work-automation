# 1日$6上限の安全性検証
haiku_cost = 0.0038  # 1回のコスト

# 1日$6で何回呼べるか
max_calls = 6.0 / haiku_cost
print(f"1日$6上限 → 最大{max_calls:.0f}回呼べる")
print(f"  案件換算: {max_calls / 1.10 / 1.15:.0f}件/日（リトライ+マージン込み）")
print(f"  現状1,114件/日 → ${1114 * 1.10 * 1.15 * haiku_cost:.2f}/日")
print()

# 20営業日で月額
for daily_limit in [5.0, 5.5, 6.0]:
    monthly = daily_limit * 20
    print(f"  日次上限${daily_limit} × 20営業日 = 月${monthly:.0f}")

print()
print("=== 前回事故（$50/日）が起きる条件 ===")
calls_for_50 = 50.0 / haiku_cost
print(f"$50/日 → {calls_for_50:.0f}回必要")
print("現状設計: 1,114件×1回 = 最大約1,409回")
print("前回事故: 17,621回（30分おき×全件×全人員の総当たり）")
print()
print("=== 新設計で$50/日になる可能性 ===")
print("新設計: 案件1件につきLLM1回だけ。処理済みIDで重複防止。")
print(f"$6/日上限 → {max_calls:.0f}回で強制停止。物理的に$6超えない。")
print(f"仮にバグで無限ループしても: {max_calls:.0f}回目で停止 → $6で打ち止め")
