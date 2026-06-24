import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

avg_input = 4000
avg_output = 800

print("=== gate_checker 第2レビュアー モデル別コスト試算 ===")
print()
print(f"前提: 1回あたり入力{avg_input}トークン / 出力{avg_output}トークン")
print(f"      月に約60回実行（1日3回 x 20営業日）")
print()

models = [
    ("Gemini 2.0 Flash (現状)", 0, 0, "無料枠枯渇で使えない"),
    ("Claude Haiku 4.5", 0.80, 4.00, "最安・速い"),
    ("Claude Sonnet 4.6", 3.00, 15.00, "コスパ良"),
    ("Claude Opus 4.6", 15.00, 75.00, "最高精度"),
    ("GPT-4o (第1レビュアー)", 2.50, 10.00, "参考: 今のGPT枠"),
]

print(f"{'モデル':<30} {'入力$/1M':>10} {'出力$/1M':>10} {'1回':>10} {'月60回':>10}")
print("-" * 75)

for name, inp, out, note in models:
    cost_per = (avg_input * inp + avg_output * out) / 1_000_000
    monthly = cost_per * 60
    print(f"{name:<30} ${inp:>8.2f} ${out:>8.2f} ${cost_per:>8.4f} ${monthly:>8.2f}  {note}")

print()
print("--- 月$140予算に対する影響 ---")
print(f"現在の月コスト: $0.55（6月19日時点）")
for name, inp, out, note in models[1:4]:
    cost_per = (avg_input * inp + avg_output * out) / 1_000_000
    monthly = cost_per * 60
    pct = monthly / 140 * 100
    print(f"  {name}: +${monthly:.2f}/月 = 予算の{pct:.1f}%")
