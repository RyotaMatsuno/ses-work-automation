import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query_cmds.txt"

with open(base + r"\line_query.py", encoding="utf-8", errors="replace") as f:
    content = f.read()

lines = content.split("\n")
# handle_line_query関数を見つける
hq_start = next((i for i, l in enumerate(lines) if "def handle_line_query" in l), 0)
hq_end = min(hq_start + 80, len(lines))
handle_fn = "\n".join(lines[hq_start:hq_end])

result = f"line_query.py ({len(content)}chars)\n\n=== handle_line_query ===\n{handle_fn}"
with open(out, "w", encoding="utf-8") as f:
    f.write(result)
print(result[:4000])
