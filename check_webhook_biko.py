import sys

sys.stdout.reconfigure(encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# LINE auto-register のフォーマットを確認
# "LINE auto-register" や "biko" や "備考" を含む行を探す
print("\n=== LINE auto-register / biko references ===")
for i, line in enumerate(lines, 1):
    raw = line
    if "auto-register" in raw or "auto_register" in raw:
        print(f"L{i}: {raw.strip()[:150]}")

print("\n=== 備考（LINEメモ）references ===")
for i, line in enumerate(lines, 1):
    if "\u5099\u8003" in line:
        print(f"L{i}: {line.strip()[:150]}")

print("\n=== register_engineer calls ===")
for i, line in enumerate(lines, 1):
    if "register_engineer" in line:
        print(f"L{i}: {line.strip()[:150]}")

print("\n=== note = / biko = construction ===")
for i, line in enumerate(lines, 1):
    if ("note =" in line or "biko =" in line) and ("LINE" in line or "\u81ea\u52d5" in line or "auto" in line):
        print(f"L{i}: {line.strip()[:150]}")
