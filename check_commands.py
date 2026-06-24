import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\webhook_commands.txt"

with open(base + r"\webhook_server.py", encoding="utf-8", errors="replace") as f:
    content = f.read()

lines = content.split("\n")

# process_message関数とコマンド分岐を抽出
pm_start = next((i for i, l in enumerate(lines) if "def process_message" in l), 0)
pm_end = min(pm_start + 120, len(lines))
process_msg = "\n".join(lines[pm_start:pm_end])

# line_query.pyが存在するか
import os

lq_path = base + r"\line_query.py"
lq_exists = os.path.exists(lq_path)
lq_size = os.path.getsize(lq_path) if lq_exists else 0

result = f"=== process_message (L{pm_start + 1}) ===\n{process_msg}\n\n=== line_query.py: exists={lq_exists} size={lq_size} ==="

with open(out, "w", encoding="utf-8") as f:
    f.write(result)
print(result[:5000])
