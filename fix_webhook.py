# -*- coding: utf-8 -*-
"""
webhook_server.py の3点修正:
1. run_reverse_matching_full の粗利上限15万フィルタを撤廃
2. 自発的push通知を松野のみ・作業進捗関連に限定
3. LINE keepaliveを短縮してコールドスタート抑制
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
content = open(WS, encoding="utf-8").read()

# ── 修正1: 粗利上限15万フィルタを撤廃 ──
OLD_FILTER = """    # ハードフィルタ: 上振れ15万超を強制除外（単価0=スキル見合いは含める）
    eng_price = engineer.get("price", 0) or 0
    if eng_price > 0:
        unique = [m for m in unique
                  if (m.get("project_price") or 0) == 0
                  or ((m.get("project_price") or 0) - eng_price) <= 15]
    return {"matches": unique}"""

NEW_FILTER = """    # 粗利上限フィルタ撤廃（2026-06-15）
    # 「単価合えば内容なんでもマッチ」方針により上限チェックなし
    return {"matches": unique}"""

if OLD_FILTER in content:
    content = content.replace(OLD_FILTER, NEW_FILTER)
    print("修正1: 粗利上限フィルタ撤廃 OK")
else:
    print("修正1: 対象箇所が見つかりません（確認要）")

# ── 修正2: push通知を松野のみ・作業進捗関連に限定 ──
# line_bridge_workerエンドポイントでのpush送信を削除（作業進捗は「作業進捗」コマンドで取得）
# 自発的pushは全て廃止し、松野がpullする形に統一
OLD_WORKER_PUSH = """        pushed = 0
        for item in results:
            if (
                item.get("user_id") == MATSUNO_USER_ID
                and item.get("message")
                and consume_completion_push_budget()
            ):
                push_message(
                    item["user_id"],
                    item["message"],
                    MATSUNO_CHANNEL_TOKEN,
                )
                pushed += 1"""

NEW_WORKER_PUSH = """        # 自発的push通知は廃止（2026-06-15）
        # 松野は「作業進捗」コマンドでLINEからpullする方式に統一
        # コスト異常・エラー等の緊急通知はhuman_review_itemsに記録し作業進捗で確認
        pushed = 0"""

if OLD_WORKER_PUSH in content:
    content = content.replace(OLD_WORKER_PUSH, NEW_WORKER_PUSH)
    print("修正2: 自発的push廃止 OK")
else:
    print("修正2: 対象箇所が見つかりません（確認要）")

# ── 修正3: keepaliveを10分→2分に短縮してコールドスタート抑制 ──
OLD_KEEPALIVE = "        time.sleep(600)"
NEW_KEEPALIVE = "        time.sleep(120)  # 2分おきにping（コールドスタート抑制）"

if OLD_KEEPALIVE in content:
    content = content.replace(OLD_KEEPALIVE, NEW_KEEPALIVE)
    print("修正3: keepalive 10分→2分 OK")
else:
    print("修正3: 対象箇所が見つかりません（確認要）")

with open(WS, "w", encoding="utf-8") as f:
    f.write(content)
print("webhook_server.py 書き込み完了")
