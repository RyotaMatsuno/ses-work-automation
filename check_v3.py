import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3"
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\v3_files.txt"

results = []
for f in [
    "CLAUDE.md",
    "SPEC.md",
    "TASKS.md",
    "structurer.py",
    "cost_guard.py",
    "notion_client.py",
    "matcher.py",
    "config.py",
]:
    p = os.path.join(base, f)
    if os.path.exists(p):
        size = os.path.getsize(p)
        results.append(f"OK  {f} ({size}bytes)")
    else:
        results.append(f"NG  {f} (not found)")

with open(out, "w", encoding="utf-8") as o:
    o.write("\n".join(results))
print("\n".join(results))
