import re

# webhook_server.pyの全call_claude呼び出し箇所を抽出
with open(
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py",
    "r",
    encoding="utf-8",
    errors="replace",
) as f:
    lines = f.readlines()

out = open("api_audit.txt", "w", encoding="utf-8")

# 1. call_claude / requests.post anthropic の全呼び出し箇所
out.write("=== Claude API呼び出し箇所 ===\n")
for i, line in enumerate(lines, 1):
    if "call_claude(" in line or ("anthropic.com/v1/messages" in line):
        # 前後3行のコンテキスト
        start = max(0, i - 4)
        end = min(len(lines), i + 2)
        out.write(f"\n--- Line {i} ---\n")
        for j in range(start, end):
            out.write(f"{j + 1}: {lines[j]}")

# 2. 各call_claude呼び出し元の関数名を特定
out.write("\n\n=== 呼び出し元関数サマリー ===\n")
current_func = ""
api_calls = []
for i, line in enumerate(lines, 1):
    m = re.match(r"^def (\w+)", line)
    if m:
        current_func = m.group(1)
    if "call_claude(" in line:
        api_calls.append(f"Line {i}: [{current_func}] {line.strip()[:80]}")

for c in api_calls:
    out.write(c + "\n")

# 3. run_reverse_matching / run_matching にcall_claudeが残っていないか確認
out.write("\n\n=== run_matching/run_reverse_matching内のAPI呼び出し確認 ===\n")
in_target = False
target_funcs = ["run_matching", "run_reverse_matching", "run_reverse_matching_full"]
current_func = ""
for i, line in enumerate(lines, 1):
    m = re.match(r"^def (\w+)", line)
    if m:
        current_func = m.group(1)
    if current_func in target_funcs and "call_claude" in line:
        out.write(f"WARNING Line {i} [{current_func}]: {line.strip()}\n")

out.write("\nAUDIT COMPLETE\n")
out.close()
print("DONE")
