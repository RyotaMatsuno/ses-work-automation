import sys

fpath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(fpath, "rb") as f:
    raw = f.read()

idx = raw.find(b"def fetch_all_pages(")
# その行末まで取得
line_end = raw.find(b"\n", idx)
old_sig = raw[idx:line_end]
new_sig = b"def fetch_all_pages(db_id: str, filter_body: dict = None) -> list[dict]:"

sys.stdout.buffer.write(b"old: " + old_sig + b"\n")
sys.stdout.buffer.write(b"new: " + new_sig + b"\n")

raw = raw[:idx] + new_sig + raw[line_end:]

# payload定義の直後にfilter_body挿入
# {"page_size": 100} の後に if filter_body を追加
old_payload = b'    payload: dict[str, Any] = {"page_size": 100}'
new_payload = (
    b'    payload: dict[str, Any] = {"page_size": 100}\n    if filter_body:\n        payload["filter"] = filter_body'
)

if old_payload in raw:
    raw = raw.replace(old_payload, new_payload, 1)
    sys.stdout.buffer.write(b"payload block updated\n")
else:
    sys.stdout.buffer.write(b"payload block not found\n")

with open(fpath, "wb") as f:
    f.write(raw)

# 検証
with open(fpath, "rb") as f:
    v = f.read().decode("utf-8", errors="replace")
idx2 = v.find("def fetch_all_pages(")
sys.stdout.buffer.write(v[idx2 : idx2 + 200].encode("utf-8", errors="replace"))
