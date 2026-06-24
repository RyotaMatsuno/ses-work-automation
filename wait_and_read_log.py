import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
time.sleep(60)
with open("codex_input_source.log", "r", encoding="utf-8", errors="replace") as f:
    content = f.read()
print(f"総文字数: {len(content)}")
# 完了キーワード検索
keywords = ["完了報告", "tokens used", "done", "Phase 5", "add_input_source_fields", "webhook_server"]
lines = content.splitlines()
for i, line in enumerate(lines):
    for k in keywords:
        if k in line:
            print(f"L{i}: {line[:120]}")
            break
print("=== 末尾1500文字 ===")
print(content[-1500:])
