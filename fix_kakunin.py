# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BRIDGE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_bridge.py"
content = open(BRIDGE, encoding="utf-8").read()

OLD = '    if stripped == "案件進捗":\n        return {"handled": True, "reply": "案件進捗機能は準備中です。"}'

NEW = """    if stripped == "確認済み":
        clear_human_review_items()
        return {"handled": True, "reply": "確認事項をクリアしました✅"}

    if stripped == "案件進捗":
        return {"handled": True, "reply": "案件進捗機能は準備中です。"}"""

if OLD in content:
    content = content.replace(OLD, NEW)
    open(BRIDGE, "w", encoding="utf-8").write(content)
    print("追加完了")
else:
    print("差し替え対象が見つかりません")
    # 現在のhandle_router_message周辺を確認
    idx = content.find("def handle_router_message")
    print(content[idx : idx + 600])
