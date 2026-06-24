import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
L = open("freee/_dry_sheet.txt", encoding="utf-8", errors="replace").read().splitlines()
roster = [l for l in L if (" | " in l and "請求" in l and "粗利" in l)]
print("=== 対象人員（Sheet基準） ===")
for l in roster:
    print(l.strip())
total = 0
for l in roster:
    try:
        total += int(l.split("請求")[1].split("円")[0].replace(",", "").strip())
    except Exception:
        pass
print("--- 集計 ---")
for l in L:
    if any(k in l for k in ["対象人員", "[dedup]", "SKIP ", "DRY-RUN完了"]):
        print(l.strip())
print("名簿の請求合計（仲山SKIP分も含む）:", format(total, ","), "円")
print("実際に新規作成される額（仲山15,000を除く）:", format(total - 15000, ","), "円")
