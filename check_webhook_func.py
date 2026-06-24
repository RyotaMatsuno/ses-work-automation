import sys

sys.stdout.reconfigure(encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# L765-L830 の register_engineer 関数を表示
print("=== webhook register_engineer L765-L835 ===")
for i in range(764, 835):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")

# L919-L940 のソース判定も確認
print("\n=== source detection L915-L935 ===")
for i in range(914, 935):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")
