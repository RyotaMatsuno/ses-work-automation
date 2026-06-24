import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# line_webhook ディレクトリ内の全Pythonファイルを対象に「マッチ案件」を検索
lw_dir = os.path.join(ses, "line_webhook")
print("=== line_webhook/ の全Pythonファイル ===")
for fname in sorted(os.listdir(lw_dir)):
    if fname.endswith(".py"):
        fpath = os.path.join(lw_dir, fname)
        size = os.path.getsize(fpath)
        print(f"  {fname} ({size:,} bytes)")

# 全ファイルで「マッチ案件」「｜」「連絡先:」を検索
print("\n=== 全ファイル: 「マッチ案件」「連絡先」「概要:」検索 ===")
for fname in sorted(os.listdir(lw_dir)):
    if not fname.endswith(".py"):
        continue
    fpath = os.path.join(lw_dir, fname)
    try:
        with open(fpath, encoding="utf-8") as f:
            lines = f.readlines()
    except:
        continue
    for i, line in enumerate(lines, 1):
        if any(
            kw in line
            for kw in [
                "\u30de\u30c3\u30c1\u6848\u4ef6",  # マッチ案件
                "\u9023\u7d61\u5148:",  # 連絡先:
                "\u6982\u8981:",  # 概要:
                "\u300cHS",  # 「HS
                "eng.*\uff5c",  # eng + ｜
                "\u30de\u30c3\u30c1\u6570",  # マッチ数
            ]
        ):
            print(f"[{fname}] L{i}: {line.rstrip()[:150]}")
