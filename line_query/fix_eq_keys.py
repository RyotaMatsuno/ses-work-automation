import os
import sys

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

# engineer_query内の化けた文字列を正しいbytesに置換
# 現在のhex（前回list_keysで確認済み）-> 正しいbytes

fixes = [
    # "スキル" engineer_skills取得用 -> e382b9e382ade383ab
    (b'"' + bytes.fromhex("e382b9e382ade383ab") + b'"', b'"' + "\u30b9\u30ad\u30eb".encode("utf-8") + b'"'),
    # "単価（万円）" engineer_rate取得用 -> e58d98e4bea1efbc88e4b887e58686efbc89
    (
        b'"' + bytes.fromhex("e58d98e4bea1efbc88e4b887e58686efbc89") + b'"',
        b'"' + "\u5358\u4fa1\uff08\u4e07\u5186\uff09".encode("utf-8") + b'"',
    ),
    # "ステータス" -> e382b9e38386e383bce382bfe382b9
    (
        b'"' + bytes.fromhex("e382b9e38386e383bce382bfe382b9") + b'"',
        b'"' + "\u30b9\u30c6\u30fc\u30bf\u30b9".encode("utf-8") + b'"',
    ),
    # "必要スキル" -> e5bf85e8a681e382b9e382ade383ab
    (
        b'"' + bytes.fromhex("e5bf85e8a681e382b9e382ade383ab") + b'"',
        b'"' + "\u5fc5\u8981\u30b9\u30ad\u30eb".encode("utf-8") + b'"',
    ),
    # "担当者" -> e68b85e5bd93e88085
    (b'"' + bytes.fromhex("e68b85e5bd93e88085") + b'"', b'"' + "\u62c5\u5f53\u8005".encode("utf-8") + b'"'),
]

# 現在ファイルに化けた文字が残っているか確認してから置換
new_raw = raw
count = 0
for old_b, new_b in fixes:
    n = new_raw.count(old_b)
    if n > 0:
        new_raw = new_raw.replace(old_b, new_b)
        count += n
        sys.stdout.buffer.write(b"Fixed " + str(n).encode() + b"x: " + new_b + b"\n")
    else:
        sys.stdout.buffer.write(b"ALREADY OK or NOT FOUND: " + old_b.hex().encode()[:30] + b"\n")

sys.stdout.buffer.write(f"Total replacements: {count}\n".encode("utf-8"))

with open(fpath, "wb") as f:
    f.write(new_raw)

# 検証: engineer_query内のプロパティキー
with open(fpath, "rb") as f:
    verify = f.read().decode("utf-8")

import re

idx = verify.find("def engineer_query")
nxt = verify.find("\ndef project_query")
eq_body = verify[idx:nxt]
calls = re.findall(r'_(?:text|select|multi_select|number)_prop\(\w+,\s*["\']([^"\']+)["\']', eq_body)
sys.stdout.buffer.write(b"\nengineer_query prop keys:\n")
for c in calls:
    sys.stdout.buffer.write(f"  {c!r}\n".encode("utf-8"))
