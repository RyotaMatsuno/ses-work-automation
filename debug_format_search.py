import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
wh_path = os.path.join(ses, "line_webhook", "webhook_server.py")
with open(wh_path, encoding="utf-8") as f:
    content = f.read()
    lines = content.split("\n")

ml_path = os.path.join(ses, "line_webhook", "matching_logic.py")
with open(ml_path, encoding="utf-8") as f:
    ml_content = f.read()
    ml_lines = ml_content.split("\n")

# 「北小金」「マッチ案件」「連絡先:」「送信元:」などのキーワードを検索
for label, text, lns in [("webhook_server", content, lines), ("matching_logic", ml_content, ml_lines)]:
    print(f"\n=== [{label}] フォーマット検索 ===")
    keywords = [
        "\u30de\u30c3\u30c1\u6848\u4ef6",  # マッチ案件
        "\u9023\u7d61\u5148:",  # 連絡先:
        "\u6982\u8981:",  # 概要:
        "nearest_station",
        "\u5317\u5c0f\u91d1",  # 北小金
        "eng_name.*\u7ad9",  # eng_name + 駅
        "\u30de\u30c3\u30c1\u6570",  # マッチ数
        "format_eng",
        "build_eng",
        "\u30a8\u30f3\u30b8\u30cb\u30a2\u767b\u9332",  # エンジニア登録
        "HS\u30012",  # HSと
    ]
    for i, line in enumerate(lns, 1):
        for kw in keywords:
            import re

            if re.search(kw, line):
                print(f"L{i}: {line[:150]}")
                break

# 「【HS｜北小金】マッチ案件 21件」の「｜」区切りと「マッチ案件」を検索
print("\n=== 「｜」 AND 「マッチ」 ===")
for label, lns in [("webhook_server", lines), ("matching_logic", ml_lines)]:
    for i, line in enumerate(lns, 1):
        if "\uff5c" in line or "|" in line:  # ｜(全角)
            if "\u30de\u30c3\u30c1" in line or "match" in line.lower():
                print(f"[{label}] L{i}: {line[:150]}")
