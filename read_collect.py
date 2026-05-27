
import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
collect_py = os.path.join(base, "outreach_system", "collect_targets.py")
with open(collect_py, encoding="utf-8") as f:
    content = f.read()
print(content[:3000])
