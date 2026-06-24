import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

# reply API は quota対象外 → 実際のreply tokenで使えば無制限
# replyトークンは LINE から実際のメッセージが来たときだけ有効（1分間有効、1回のみ）

# ============================================================
# 本番動作確認の方法:
# 「松野が実際にLINEから「HS 北小金」と送る」
# → webhook_server.py が受信
# → handle_line_query("HS 北小金") → 結果文字列
# → reply_message(reply_token, result, token) → LINEに返信
# ============================================================

# まずCloud Run上でhandle_line_queryが正しく呼ばれるかをログで確認するため
# webhook に実際のイベントを送り、Cloud Runのログで追跡する

# ただし push API は制限に達しているので、ローカルで完全模擬テストを行う
# process_message のロジックを完全に再現

print("=== process_message 完全ローカル模擬テスト ===")
print()

# 1. handle_line_query の動作確認
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
for m in list(sys.modules):
    if "line_query" in m:
        del sys.modules[m]
from line_query import handle_line_query

test_inputs = [
    "HS 北小金",
    "H.S 北小金",
    "hs 北小金",
    "H.S　北小金",
    "HS/北小金",
    "OA 森林公園",
    "おつかれさまです！\n【名 前】H.S\nよろしくお願いします",  # スキルシート本文
]

all_ok = True
for txt in test_inputs:
    result = handle_line_query(txt)
    short_txt = txt.replace("\n", " ")[:20]
    if result is None:
        print(f"  → [{short_txt}] None (classify_messageへ) ✅")
    elif "マッチ案件" in result or "マッチ人員" in result:
        lines = result.split("\n")
        print(f"  → [{short_txt}] ✅ {lines[0]}")
    elif "一致する" in result:
        # これが来てはいけない（handle_line_queryがNoneに変換するはず）
        print(f"  → [{short_txt}] ❌ 一致なし文字列が返ってきた: {result[:50]}")
        all_ok = False
    else:
        print(f"  → [{short_txt}] 結果: {result[:50]}")

print()
print(f"結果: {'✅ 全テストOK' if all_ok else '❌ 要修正'}")
print()
print("=== 「HS 北小金」の実際の返答内容 ===")
r = handle_line_query("HS 北小金")
if r:
    print(r[:2000])
