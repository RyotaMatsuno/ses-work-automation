import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# 1. LINEに届いたフォーマット「マッチ案件 21件」はwebhook_server.pyのline_queryから来ている可能性
# webhook_server.py で "マッチ" や "粗利" を検索
wh_path = os.path.join(ses, "line_webhook", "webhook_server.py")
with open(wh_path, encoding="utf-8") as f:
    wh_lines = f.readlines()

print("=== webhook_server.py: マッチ/粗利/21件/上位 ===")
for i, line in enumerate(wh_lines, 1):
    if any(
        kw in line
        for kw in [
            "\u30de\u30c3\u30c1",
            "match",
            "\u7c97\u5229",
            "gross",
            "\u4e0a\u4f4d",
            "top",
            "21\u4ef6",
            "\u9023\u7d61\u5148",
            "contact",
            "\u5358\u4fa1: ",
            "price",
            "\u2460",
            "\u2461",
            "\u2462",  # ①②③
            "format_match",
            "build_match",
            "\u6848\u4ef6\u540d",
        ]
    ):
        print(f"L{i}: {line.rstrip()[:150]}")

# 2. sales_pipeline も確認
sp_path = os.path.join(ses, "sales_pipeline")
if os.path.exists(sp_path):
    for fname in os.listdir(sp_path):
        if fname.endswith(".py"):
            fpath = os.path.join(sp_path, fname)
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            if "\u30de\u30c3\u30c1" in content or "gross" in content:
                print(f"\n[{fname}] contains match/gross")
                # 関連行を出力
                for i, line in enumerate(content.split("\n"), 1):
                    if any(
                        kw in line
                        for kw in [
                            "\u7c97\u5229",
                            "gross",
                            "\u4e0a\u4f4d",
                            "top",
                            "21\u4ef6",
                            "\u9023\u7d61\u5148",
                            "\u5358\u4fa1: ",
                        ]
                    ):
                        print(f"  L{i}: {line.rstrip()[:150]}")
