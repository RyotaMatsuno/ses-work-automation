import sys

fpath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(fpath, "rb") as f:
    raw = f.read()

# 正しい募集中のbytes: e58b9fe99b86e4b8ad
bosku_bytes = bytes.fromhex("e58b9fe99b86e4b8ad")

# まず定数ブロックの VAL_RECRUITING を正しいhexに更新
old_const = b"VAL_RECRUITING = bytes.fromhex('e5aea1e99b86e4b8ad').decode(\"utf-8\")"
new_const = b"VAL_RECRUITING = bytes.fromhex('e58b9fe99b86e4b8ad').decode(\"utf-8\")"
new_raw = raw.replace(old_const, new_const)

if new_raw == raw:
    sys.stdout.buffer.write(b"const not found, searching...\n")
    idx = raw.find(b"VAL_RECRUITING = bytes")
    if idx >= 0:
        sys.stdout.buffer.write(b"Found: " + raw[idx : idx + 60].hex().encode() + b"\n")
else:
    sys.stdout.buffer.write(b"Updated VAL_RECRUITING const\n")

# "募集中" の文字列リテラルを VAL_RECRUITING に置換
for quote in [b'"', b"'"]:
    old = quote + bosku_bytes + quote
    new = b"VAL_RECRUITING"
    if old in new_raw:
        cnt = new_raw.count(old)
        new_raw = new_raw.replace(old, new)
        sys.stdout.buffer.write(f'  Replaced {cnt}x "募集中"\n'.encode())

with open(fpath, "wb") as f:
    f.write(new_raw)

# 検証
with open(fpath, "rb") as f:
    v = f.read().decode("utf-8")
idx = v.find("def engineer_query")
nxt = v.find("\ndef project_query")
eq = v[idx:nxt]
sys.stdout.buffer.write(f"VAL_RECRUITING in engineer_query: {('VAL_RECRUITING' in eq)}\n".encode())
# 実際の != 行を表示
for line in eq.split("\n"):
    if "!=" in line and "status" in line.lower():
        sys.stdout.buffer.write(f"  status check: {line.strip()!r}\n".encode())
