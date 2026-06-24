import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 既存LINE通知関数を探す
import subprocess

result = subprocess.run(
    [
        "python",
        "-c",
        """
import os
hits = []
for root, dirs, files in os.walk("."):
    if "__pycache__" in root or "_archive_tmp" in root or ".git" in root:
        continue
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(root, f)
            try:
                with open(p, encoding="utf-8") as fh:
                    content = fh.read()
                if "push_message" in content and "line" in content.lower():
                    hits.append(p)
            except: pass
print("\\n".join(hits[:15]))
""",
    ],
    capture_output=True,
    text=True,
)
print(result.stdout)
