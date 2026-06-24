# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# モジュールリロード
import importlib

import line_webhook.line_bridge as lb

importlib.reload(lb)

# テスト用に確認事項を追加してからクリア
lb.add_human_review_item("テスト確認事項")
print("追加後:", lb.get_human_review_items())

r = lb.handle_router_message("確認済み", "test", "m", 0)
print("確認済みコマンド:", r)
print("クリア後:", lb.get_human_review_items())
