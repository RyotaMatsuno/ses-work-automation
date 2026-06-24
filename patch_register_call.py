import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
path = os.path.join(base, "mail_pipeline", "mail_pipeline.py")
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# 817行目（0-indexed: 816）を修正
print("Before 817:", repr(lines[816]))
old = lines[816]
new = old.replace(
    "register_project(info, subject, sender, input_source, affiliation)",
    "register_project(info, subject, sender, input_source, affiliation, raw_body=body)",
)
print("After  817:", repr(new))

if old != new:
    lines[816] = new
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("PATCH_CALL: OK")
else:
    print("PATCH_CALL: no change")

import py_compile

try:
    py_compile.compile(path, doraise=True)
    print("SYNTAX: OK")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
