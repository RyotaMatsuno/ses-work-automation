path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\requirements.txt"
with open(path, "r") as f:
    content = f.read()

# line_query.py の依存パッケージを追加
additions = ["jpholiday", "python-dateutil", "anthropic"]
for pkg in additions:
    if pkg not in content:
        content = content.rstrip() + f"\n{pkg}\n"

with open(path, "w") as f:
    f.write(content)

print("Updated requirements.txt:")
print(content)
