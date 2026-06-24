import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# notify_line.py 全体を確認（粗利計算・表示件数・LINEメッセージ生成部分）
notify_path = os.path.join(ses, "matching_v2", "notify_line.py")
with open(notify_path, encoding="utf-8") as f:
    lines = f.readlines()

print(f"notify_line.py: {len(lines)} lines")
print("\n=== 全行（粗利・単価・上位・件数関連）===")
for i, line in enumerate(lines, 1):
    stripped = line.rstrip()
    if any(
        kw in stripped
        for kw in [
            "gross",
            "margin",
            "profit",
            "\u7c97\u5229",
            "\u5358\u4fa1",
            "price",
            "cost",
            "\u4e0a\u4f4d",
            "top",
            "limit",
            "slice",
            "[:5]",
            "[:3]",
            "[:10]",
            "format_match",
            "build_message",
            "LINE\u30e1\u30c3\u30bb\u30fc\u30b8",
            "send",
            "\u63d0\u6848\u5358\u4fa1",
            "\u539f\u4fa1",
            "engineer_price",
            "project_price",
        ]
    ):
        print(f"L{i}: {stripped}")

# matching_v2.py も確認
mv2_path = os.path.join(ses, "matching_v2", "matching_v2.py")
if os.path.exists(mv2_path):
    with open(mv2_path, encoding="utf-8") as f:
        mv2_lines = f.readlines()
    print(f"\n\nmatching_v2.py: {len(mv2_lines)} lines")
    print("\n=== 粗利・単価計算・スコア関連 ===")
    for i, line in enumerate(mv2_lines, 1):
        stripped = line.rstrip()
        if any(
            kw in stripped
            for kw in [
                "gross",
                "margin",
                "profit",
                "\u7c97\u5229",
                "\u5358\u4fa1",
                "price",
                "cost",
                "score",
                "\u30b9\u30b3\u30a2",
                "threshold",
                "\u9598\u5024",
                "min_",
                "engineer_price",
                "project_price",
                "\u63d0\u6848\u5358\u4fa1",
            ]
        ):
            print(f"L{i}: {stripped}")
