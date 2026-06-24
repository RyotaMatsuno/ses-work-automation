# 最終コストシミュレーション - モデル差し替え × 重複除去 × embedding絞り込み

# 実データ
total_2days = 3767
unique_2days = 2228  # 重複除去後
unique_per_day = unique_2days // 2  # 1日あたり
engineers = 143

# トークン数（実績）
input_tok = 6134
output_tok = 1123

# 各モデルの1回あたりコスト（Batch API）
models = {
    "Claude Haiku（現状）": (1.00, 5.00),  # 現行
    "Gemini 2.5 Flash-Lite Batch": (0.05, 0.20),
    "GPT-4.1-nano Batch": (0.05, 0.20),
    "Amazon Nova Micro Batch": (0.0175, 0.07),
}

rate = 155  # JPY/USD

print("=" * 70)
print("重複除去後の案件数/日:", unique_per_day, "件")
print("エンジニア:", engineers, "人")
print("=" * 70)

for model, (in_price, out_price) in models.items():
    cost_per_call = input_tok * in_price / 1_000_000 + output_tok * out_price / 1_000_000

    print(f"\n【{model}】 1回=${cost_per_call:.6f}")

    # パターン1: 全組み合わせ（参考）
    all_pairs = unique_per_day * engineers
    daily_all = all_pairs * cost_per_call
    print(
        f"  全組み合わせ: {all_pairs:,}回/日 → ${daily_all:.2f}/日 → 月${daily_all * 30:.0f} / {daily_all * 30 * rate:,.0f}円"
    )

    # パターン2: embedding上位10件に絞り込み
    top10 = unique_per_day * 10
    daily10 = top10 * cost_per_call
    print(
        f"  embedding上位10件: {top10:,}回/日 → ${daily10:.2f}/日 → 月${daily10 * 30:.0f} / {daily10 * 30 * rate:,.0f}円"
    )

    # パターン3: embedding上位5件に絞り込み
    top5 = unique_per_day * 5
    daily5 = top5 * cost_per_call
    print(f"  embedding上位5件:  {top5:,}回/日 → ${daily5:.2f}/日 → 月${daily5 * 30:.0f} / {daily5 * 30 * rate:,.0f}円")

print("\n" + "=" * 70)
print("※embeddingフィルタ（ruri-v3ローカル）= 無料")
print("※重複除去（ハッシュ）= 無料")
print("=" * 70)
