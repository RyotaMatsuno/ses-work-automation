import sys

sys.stdout.reconfigure(encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# 誤字修正: 松里LINE -> 松野LINE（2箇所）
old1 = "\u677e\u91ccLINE"  # 松里LINE（誤）
new1 = "\u677e\u91ceLINE"  # 松野LINE（正）

count = content.count(old1)
print(f"'松里LINE' found: {count} times")

content = content.replace(old1, new1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

# 確認
with open(path, encoding="utf-8") as f:
    lines = f.readlines()
print("\n=== L805-L815 after fix ===")
for i in range(804, 815):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")

# 念のため残存確認
remaining = content.count(old1)
print(f"\n残存 '松里LINE': {remaining}")
