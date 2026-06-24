import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# webhook_server.pyの285行目周辺を確認
wh = os.path.join(base, "line_webhook", "webhook_server.py")
with open(wh, encoding="utf-8") as f:
    lines = f.readlines()

for i in range(278, 340):
    line = lines[i].encode("cp932", errors="replace").decode("cp932")
    print(f"{i + 1}: {line}", end="")
