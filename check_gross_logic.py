import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
lq_path = os.path.join(lw, "line_query.py")
with open(lq_path, encoding="utf-8") as f:
    lines = f.readlines()

# 粗利上限・下限チェック箇所を全部洗い出す
print("=== 粗利・単価・budget関連の全ロジック ===")
for i, line in enumerate(lines, 1):
    stripped = line.rstrip()
    if any(
        kw in stripped
        for kw in [
            "gross",
            "budget",
            "thresh",
            "calc_gross",
            "> 15",
            "< 5",
            "< 3",
            "continue",
            "GROSS_THRESHOLD",
            "150",
            "budget > ",
        ]
    ):
        print(f"L{i}: {stripped}")
