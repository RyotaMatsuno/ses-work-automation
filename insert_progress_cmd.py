import sys
sys.stdout.reconfigure(encoding='utf-8')

wh_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(wh_path, encoding="utf-8") as f:
    content = f.read()

# マッチングブロックの return\n\n\n\n    if の直前に進捗ブロックを挿入
old = '        return\n\n\n\n    if is_send_ok or is_send_all:'

new = '''        return\n\n\n\n    # 案件進捗照会\n    if "\\u9032\\u6357" in text_stripped and len(text_stripped) <= 6:\n        progress_reply = build_progress_reply()\n        chunks = split_line_message(progress_reply)\n        reply_message(reply_token, chunks[0], sender_token)\n        push_user_id = user_id or (MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID)\n        for chunk in chunks[1:]:\n            push_message(push_user_id, chunk, sender_token)\n        return\n\n\n\n    if is_send_ok or is_send_all:'''

if old in content:
    content = content.replace(old, new, 1)
    with open(wh_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("進捗コマンド分岐 挿入OK")
else:
    # 実際の文字を確認
    idx = content.find('        return\n\n\n\n    if')
    print(f"パターンpos: {idx}")
    print(repr(content[idx:idx+60]))
