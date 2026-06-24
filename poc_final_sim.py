import numpy as np

daily_projects = 1114
num_engineers = 154
BATCH_SIZE = 30
INPUT_PER_BATCH = 1250
OUTPUT_PER_BATCH = 50

models = {
    "Nova Micro": (0.035, 0.14),
    "Nova Micro Batch": (0.0175, 0.07),
    "Gemini FL-Lite": (0.10, 0.40),
    "Gemini FL-Lite Batch": (0.05, 0.20),
    "GPT-4.1-nano Batch": (0.05, 0.20),
    "Claude Haiku(ref)": (1.00, 5.00),
}

# === パターン1: 全案件バッチ ===
calls_all = num_engineers * int(np.ceil(daily_projects / BATCH_SIZE))
print("=== Pattern1: 全案件バッチ 30件/回 ===")
print(f"1日の呼び出し: {calls_all}回")
for name, (inp, outp) in models.items():
    c = INPUT_PER_BATCH * inp / 1e6 + OUTPUT_PER_BATCH * outp / 1e6
    m = calls_all * c * 30
    flag = "OK" if m <= 150 else "OVER"
    print(f"  {name:25s}: month ${m:8.1f} / {m * 155:>10,.0f}JPY [{flag}]")

# === パターン2: ルールフィルタ+バッチ ===
matched_per_eng = int(1114 * 0.77 * 0.322) + int(1114 * 0.23)
calls_filtered = num_engineers * int(np.ceil(matched_per_eng / BATCH_SIZE))
print(f"\n=== Pattern2: ルールフィルタ+バッチ ({matched_per_eng}件/人) ===")
print(f"1日の呼び出し: {calls_filtered}回")
for name, (inp, outp) in models.items():
    c = INPUT_PER_BATCH * inp / 1e6 + OUTPUT_PER_BATCH * outp / 1e6
    m = calls_filtered * c * 30
    flag = "OK" if m <= 150 else "OVER"
    print(f"  {name:25s}: month ${m:8.1f} / {m * 155:>10,.0f}JPY [{flag}]")

# === パターン3: 重複除去+ルールフィルタ+バッチ+スキルなし除外 ===
# スキルなし案件はマッチング対象外（本文にスキル情報なし→判定不能）
matched_skill_only = int(1114 * 0.77 * 0.322)
calls_skillonly = num_engineers * int(np.ceil(matched_skill_only / BATCH_SIZE))
print(f"\n=== Pattern3: スキルなし除外+ルールフィルタ+バッチ ({matched_skill_only}件/人) ===")
print(f"1日の呼び出し: {calls_skillonly}回")
for name, (inp, outp) in models.items():
    c = INPUT_PER_BATCH * inp / 1e6 + OUTPUT_PER_BATCH * outp / 1e6
    m = calls_skillonly * c * 30
    flag = "OK" if m <= 150 else "OVER"
    print(f"  {name:25s}: month ${m:8.1f} / {m * 155:>10,.0f}JPY [{flag}]")

# === パターン4: バッチサイズを50に ===
BATCH50 = 50
INPUT50 = 2000  # 50件分
OUTPUT50 = 80
calls_50 = num_engineers * int(np.ceil(matched_skill_only / BATCH50))
print(f"\n=== Pattern4: 50件/回バッチ+スキルフィルタ ({matched_skill_only}件/人) ===")
print(f"1日の呼び出し: {calls_50}回")
for name, (inp, outp) in models.items():
    c = INPUT50 * inp / 1e6 + OUTPUT50 * outp / 1e6
    m = calls_50 * c * 30
    flag = "OK" if m <= 150 else "OVER"
    print(f"  {name:25s}: month ${m:8.1f} / {m * 155:>10,.0f}JPY [{flag}]")
