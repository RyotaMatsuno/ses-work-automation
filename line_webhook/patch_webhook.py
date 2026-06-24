# -*- coding: utf-8 -*-
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """    if msg_type == "engineer":
        try:
            buffer_key = user_id or (MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID)
            USER_BUFFER[buffer_key] = {"summary": text, "timestamp": time.time()}
        except Exception as e:
            print(f"[USER_BUFFER] save error: {e}")



    if msg_type == "engineer":

        success, reason = register_engineer(info, text, sender, user_id=user_id)"""

new = """    if msg_type == "engineer":
        try:
            buffer_key = user_id or (MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID)
            USER_BUFFER[buffer_key] = {"summary": text, "timestamp": time.time()}
            reply_message(reply_token, "\u30b9\u30ad\u30eb\u30b7\u30fc\u30c8\uff08PDF/Excel/Word\uff09\u3092\u9001\u3063\u3066\u304f\u3060\u3055\u3044\u3002", sender_token)
        except Exception as e:
            print(f"[USER_BUFFER] save error: {e}")
        return

    if False and msg_type == "engineer":  # \u30d5\u30a1\u30a4\u30eb\u53d7\u4fe1\u5f85\u6a5f\u30d5\u30ed\u30fc\u306b\u4e00\u672c\u5316\uff08\u6b64\u30d6\u30ed\u30c3\u30af\u306f\u4f7f\u308f\u306a\u3044\uff09

        success, reason = register_engineer(info, text, sender, user_id=user_id)"""

if old in content:
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("PATCHED OK")
else:
    print("PATTERN NOT FOUND - checking actual content:")
    idx = content.find("USER_BUFFER[buffer_key]")
    print(repr(content[idx - 100 : idx + 300]))
