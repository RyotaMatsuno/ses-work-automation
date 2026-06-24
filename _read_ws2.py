import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("line_webhook/webhook_server.py", "rb") as f:
    raw = f.read()
content = raw.decode("cp932", errors="replace")

# handle_line_query の呼び出し前後 500文字を表示
idx = content.find("handle_line_query")
print("=== handle_line_query 呼び出し周辺 ===")
print(content[max(0, idx - 200) : idx + 1500])
