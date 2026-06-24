import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
with open("codex_input_source.log", "r", encoding="utf-8", errors="replace") as f:
    content = f.read()
print(f"総文字数: {len(content)}")
print("=== 末尾3000文字 ===")
print(content[-3000:])
