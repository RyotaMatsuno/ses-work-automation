import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# バイナリで読んでUTF-8デコード
with open("line_webhook/matching_logic.py", "rb") as f:
    raw = f.read()

# UTF-8として周辺抽出
target = "マッチ案件なし".encode("utf-8")
idx = raw.find(target)
print(f"utf-8 idx={idx}")
if idx != -1:
    chunk = raw[max(0, idx - 600) : idx + 800]
    print(chunk.decode("utf-8", errors="replace"))
