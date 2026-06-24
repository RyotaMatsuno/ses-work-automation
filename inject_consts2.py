import sys

fpath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"

props = {
    "PROP_INI": "e382a4e3838be382b7e383a3e383ab",
    "PROP_NAME": "e5908de5898d",
    "PROP_STA": "e69c80e5af84e3828ae9a785",
    "PROP_MEMO": "e58299e88083efbc884c494e45e383a1e383a2efbc89",
    "PROP_SKILL": "e382b9e382ade383ab",
    "PROP_RATE": "e58d98e4bea1efbc88e4b887e58686efbc89",
    "PROP_STATUS": "e382b9e38386e383bce382bfe382b9",
    "PROP_REQSK": "e5bf85e8a681e382b9e382ade383ab",
    "PROP_OPTSK": "e5b09ae58fafe382b9e382ade383ab",
    "PROP_ASSIGNEE": "e68b85e5bd93e88085",
    "PROP_PJNAME": "e6a188e4bbb6e5908d",
    "PROP_PJDETAIL": "e6a188e4bbb6e8a9b3e7b4b0",
    "PROP_REMOTE": "e383aae383a2e383bce38388",
    "PROP_LOCATION": "e58ba4e58b99e59cb0",
    "PROP_PERIOD": "e69c9fe99693",
    "PROP_INTERVIEW": "e99da2e8ab87e5b88ce69c9b",
    "PROP_WORKON": "e7a8bce5838de58fafe883bde697a5",
    "PROP_WORKST": "e7a8bce5838de78ab6e6b381",
    "PROP_AFFIL": "e68980e5b19ee4bc9ae7a4be",
    "VAL_RECRUITING": "e5aea1e99b86e4b8ad",
}

with open(fpath, "rb") as f:
    raw = f.read()

# 定数ブロック構築（全ASCII）
lines = [b"# === Notion property key constants (UTF-8 bytes, ASCII-safe) ==="]
for name, hexval in props.items():
    line = name.encode() + b" = bytes.fromhex(" + repr(hexval).encode() + b').decode("utf-8")'
    lines.append(line)
lines.append(b"# ================================================================")
lines.append(b"")
const_block = b"\n".join(lines) + b"\n"

marker = b"logger = logging.getLogger(__name__)"
idx = raw.find(marker)
if idx == -1:
    sys.stdout.buffer.write(b"marker not found\n")
    sys.exit(1)

line_end = raw.find(b"\n", idx) + 1
new_raw = raw[:line_end] + b"\n" + const_block + raw[line_end:]

with open(fpath, "wb") as f:
    f.write(new_raw)

sys.stdout.buffer.write(f"Written {len(new_raw)} bytes, consts={len(props)}\n".encode())

# 検証
with open(fpath, "rb") as f:
    v = f.read().decode("utf-8")
for name in ["PROP_STATUS", "VAL_RECRUITING", "PROP_SKILL"]:
    sys.stdout.buffer.write(f"{name} in file: {name in v}\n".encode())
