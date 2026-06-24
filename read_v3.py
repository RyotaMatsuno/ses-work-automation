import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3"
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\v3_read.txt"

content = {}
for f in ["TASKS.md", "structurer.py", "cost_guard.py", "matcher.py", "config.py"]:
    p = base + "\\" + f
    with open(p, encoding="utf-8") as fp:
        content[f] = fp.read()

combined = ""
for k, v in content.items():
    combined += f"\n\n===== {k} =====\n{v}"

with open(out, "w", encoding="utf-8") as o:
    o.write(combined)
print(f"Written {len(combined)} chars")
