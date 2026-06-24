import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"

with open(base + r"\line_query.py", encoding="utf-8", errors="replace") as f:
    content = f.read()
lines = content.split("\n")


# format_project_result末尾（ループ後のfooter）
def fn_range(name):
    start = next((i for i, l in enumerate(lines) if f"def {name}" in l), 0)
    end = start + 1
    while end < len(lines):
        if lines[end].startswith("def ") and end > start + 2:
            break
        end += 1
    return start, end


s1, e1 = fn_range("format_project_result")
s2, e2 = fn_range("format_engineer_result")

print("=== format_project_result 末尾10行 ===")
print("\n".join(lines[e1 - 10 : e1]))
print("\n=== format_engineer_result ===")
print("\n".join(lines[s2:e2]))

# 構文チェック
r = subprocess.run("python -m py_compile line_query.py && echo SYNTAX_OK", shell=True, capture_output=True, cwd=base)
print("\n=== 構文チェック ===")
print(r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace"))
