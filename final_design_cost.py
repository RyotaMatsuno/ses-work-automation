# GPT/Gemini壁打ち結果を反映した最終コスト試算
# 設計変更: LLMは「案件の構造化（JSON抽出）」のみ。マッチングはPython。

daily_unique = 1114  # 実測値
rate = 155

# 構造化プロンプトのトークン見積もり（GPT/Geminiの指摘を反映）
# メール本文500文字 ≒ 800tok（日本語は1文字1.5tok想定）
# システムプロンプト+Few-Shot: 500tok
# 出力JSON: 200tok
INPUT_TOK = 1300  # 本文800 + プロンプト500
OUTPUT_TOK = 200  # 構造化JSON

models = {
    "Claude Haiku 4.5": (1.00, 5.00),
    "Gemini 2.5 Flash-Lite": (0.10, 0.40),
    "GPT-4.1-nano": (0.10, 0.40),
    "Nova Micro": (0.035, 0.14),
}

print("=" * 60)
print("新設計: LLMは構造化のみ、マッチングはPython")
print(f"1日のLLM呼び出し: {daily_unique}回（案件1件1回）")
print(f"入力: {INPUT_TOK}tok, 出力: {OUTPUT_TOK}tok")
print("=" * 60)

for name, (inp, outp) in models.items():
    cost_per_call = INPUT_TOK * inp / 1e6 + OUTPUT_TOK * outp / 1e6
    daily = daily_unique * cost_per_call
    monthly = daily * 30
    print(f"  {name:25s}: ${cost_per_call:.6f}/回 x {daily_unique}/日")
    print(f"    月${monthly:.1f} / {monthly * rate:,.0f}円")
    print()

# 保守的見積もり（本文1000文字=1500tok, Few-Shot多め=800tok）
print("=" * 60)
print("保守的見積もり（入力2300tok / 出力300tok）")
print("=" * 60)
INPUT2 = 2300
OUTPUT2 = 300
for name, (inp, outp) in models.items():
    cost_per_call = INPUT2 * inp / 1e6 + OUTPUT2 * outp / 1e6
    monthly = daily_unique * cost_per_call * 30
    print(f"  {name:25s}: 月${monthly:.1f} / {monthly * rate:,.0f}円")

# リトライ10%込み
print()
print("=" * 60)
print("保守的 + リトライ10% + エラー処理込み（×1.15）")
print("=" * 60)
for name, (inp, outp) in models.items():
    cost_per_call = INPUT2 * inp / 1e6 + OUTPUT2 * outp / 1e6
    monthly = daily_unique * cost_per_call * 30 * 1.15
    flag = "OK" if monthly <= 150 else "OVER"
    print(f"  {name:25s}: 月${monthly:.1f} / {monthly * rate:,.0f}円 [{flag}]")
