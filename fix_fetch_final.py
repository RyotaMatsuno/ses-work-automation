import subprocess
import sys

SRC = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(SRC, "rb") as f:
    raw = f.read()

# payload 行の後に filter_body 処理を直接bytesで挿入
old = b'    payload: dict[str, Any] = {"page_size": 100}\n\n\n\n    while True:'
new = b'    payload: dict[str, Any] = {"page_size": 100}\n    if filter_body:\n        payload["filter"] = filter_body\n    while True:'

if old in raw:
    raw = raw.replace(old, new, 1)
    sys.stdout.buffer.write(b"filter_body added to fetch_all_pages\n")
else:
    # パターンを柔軟に探す
    idx = raw.find(b'payload: dict[str, Any] = {"page_size": 100}')
    if idx >= 0:
        end = raw.find(b"while True:", idx)
        # idxからend間のbytesを置換
        old2 = raw[idx:end]
        new2 = b'payload: dict[str, Any] = {"page_size": 100}\n    if filter_body:\n        payload["filter"] = filter_body\n    '
        raw = raw[:idx] + new2 + raw[end:]
        sys.stdout.buffer.write(b"filter_body added (flexible)\n")
    else:
        sys.stdout.buffer.write(b"ERROR: payload line not found\n")

with open(SRC, "wb") as f:
    f.write(raw)

result = subprocess.run(
    ["python", "-m", "py_compile", SRC], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
sys.stdout.buffer.write(f"Syntax: {'OK' if result.returncode == 0 else result.stderr}\n".encode())

# fetch_all_pages 確認
text = raw.decode("utf-8", errors="replace")
idx = text.find("def fetch_all_pages(")
nxt = text.find("\ndef ", idx + 5)
sys.stdout.buffer.write(text[idx:nxt].encode("utf-8", errors="replace"))
