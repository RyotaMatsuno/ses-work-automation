# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

from line_webhook.line_bridge import get_human_review_items, handle_router_message

# 現在の確認事項
items = get_human_review_items()
print(f"現在の確認事項: {len(items)}件 → {items}")

# 「確認済み」コマンドのテスト
r = handle_router_message("確認済み", "test", "m", 0)
print(f"確認済みコマンド: {r}")

# クリア後の状態
items_after = get_human_review_items()
print(f"クリア後: {len(items_after)}件")
