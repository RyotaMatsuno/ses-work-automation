# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 「詳細」コマンドをprocess_messageの最初で処理するよう修正
WS = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
content = open(WS, encoding="utf-8").read()

# route_line_messageの呼び出しブロックを確認
# 現在: route_line_message → handle_line_query の順
# 修正: 「詳細」で始まるメッセージはroute_line_messageをスキップしてhandle_line_queryへ

OLD = """    if user_id == MATSUNO_USER_ID:
        try:
            route_result = route_line_message(
                text_stripped,
                user_id,
                message_id,
                event_timestamp_ms or int(time.time() * 1000),
                reply_token,
            )
            if route_result.get("action") == "reply":
                reply_message(reply_token, route_result["text"], sender_token)
                return
            if route_result.get("action") == "immediate":
                text = route_result["text"]
                text_stripped = text.strip()
        except Exception as e:
            print(f"[line_bridge] router error: {e}")
            reply_message(
                reply_token,
                "作業キュー登録に失敗しました。キュー設定を確認してください。",
                sender_token,
            )
            return

    import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'line_query')); from line_query import handle_line_query
    result = handle_line_query(text)"""

NEW = """    # 「詳細」コマンドはroute_line_messageをスキップしてhandle_line_queryへ直接渡す
    import sys as _sys_lq; _sys_lq.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'line_query')); from line_query import handle_line_query
    if text_stripped.startswith("詳細"):
        result = handle_line_query(text_stripped)
        if result is not None:
            chunks = split_line_message(result)
            reply_message(reply_token, chunks[0], sender_token)
            for chunk in chunks[1:]:
                push_message(user_id, chunk, sender_token)
            return

    if user_id == MATSUNO_USER_ID:
        try:
            route_result = route_line_message(
                text_stripped,
                user_id,
                message_id,
                event_timestamp_ms or int(time.time() * 1000),
                reply_token,
            )
            if route_result.get("action") == "reply":
                reply_message(reply_token, route_result["text"], sender_token)
                return
            if route_result.get("action") == "immediate":
                text = route_result["text"]
                text_stripped = text.strip()
        except Exception as e:
            print(f"[line_bridge] router error: {e}")
            reply_message(
                reply_token,
                "作業キュー登録に失敗しました。キュー設定を確認してください。",
                sender_token,
            )
            return

    result = handle_line_query(text)"""

if OLD in content:
    content = content.replace(OLD, NEW)
    open(WS, "w", encoding="utf-8").write(content)
    print("詳細コマンド優先処理 修正OK")
else:
    print("ERROR: 対象箇所が見つかりません")
