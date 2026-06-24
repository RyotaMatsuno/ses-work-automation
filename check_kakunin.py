# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BRIDGE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_bridge.py"
content = open(BRIDGE, encoding="utf-8").read()

# 確認済みコマンドが handle_router_message に入っているか確認
if "確認済み" in content:
    # どこに入っているか確認
    idx = content.find("確認済み")
    print("現在の位置:")
    print(content[max(0, idx - 100) : idx + 150])
else:
    print("確認済みコマンドが見つかりません")
