import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
path = os.path.join(base, "mail_pipeline", "mail_pipeline.py")
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# 532行目: register_project の note (案件) → raw_body優先に変更
# 562行目: register_engineer の note (人材) → こちらはraw_body優先に変更しない（別途検討）

# 532行目を修正
old_note = lines[531]  # 0-indexed
print("Before 532:", repr(old_note))

# info.get('note','') → raw_body or info.get('note','')
new_note = old_note.replace("{info.get('note','')}", "{raw_body or info.get('note','')}")
print("After  532:", repr(new_note))

if old_note != new_note:
    lines[531] = new_note
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("PATCH3: OK")
else:
    print("PATCH3: no change (string not found)")

import py_compile

try:
    py_compile.compile(path, doraise=True)
    print("SYNTAX: OK")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
