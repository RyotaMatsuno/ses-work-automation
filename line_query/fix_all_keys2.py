import os
import sys

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

prop_map = {
    bytes.fromhex("e382a4e3838be382b7e383a3e383ab"): "\u30a4\u30cb\u30b7\u30e3\u30eb",
    bytes.fromhex("e382b9e382ade383ab"): "\u30b9\u30ad\u30eb",
    bytes.fromhex("e382b9e38386e383bce382bfe382b9"): "\u30b9\u30c6\u30fc\u30bf\u30b9",
    bytes.fromhex("e383aae383a2e383bce38388"): "\u30ea\u30e2\u30fc\u30c8",
    bytes.fromhex("e58299e88083efbc884c494e45e383a1e383a2efbc89"): "\u5099\u8003\uff08LINE\u30e1\u30e2\uff09",
    bytes.fromhex("e58ba4e58b99e59cb0"): "\u52d9\u5c45\u5730",
    bytes.fromhex("e58d98e4bea1efbc88e4b887e58686efbc89"): "\u5355\u4fa1\uff08\u4e07\u5186\uff09",
    bytes.fromhex("e5908de5898d"): "\u540d\u524d",
    bytes.fromhex("e5b09ae58fafe382b9e382ade383ab"): "\u5c1a\u53ef\u30b9\u30ad\u30eb",
    bytes.fromhex("e5bf85e8a681e382b9e382ade383ab"): "\u5fc5\u8981\u30b9\u30ad\u30eb",
    bytes.fromhex("e68980e5b19ee4bc9ae7a4be"): "\u6240\u5c5e\u4f1a\u793e",
    bytes.fromhex("e68b85e5bd93e88085"): "\u62c5\u5f53\u8005",
    bytes.fromhex("e69c80e5af84e3828ae9a785"): "\u6700\u5bc4\u308a\u99c5",
    bytes.fromhex("e69c9fe99693"): "\u671f\u9593",
    bytes.fromhex("e6a188e4bbb6e5908d"): "\u6848\u4ef6\u540d",
    bytes.fromhex("e6a188e4bbb6e8a9b3e7b4b0"): "\u6848\u4ef6\u8a73\u7d30",
    bytes.fromhex("e7a8bce5838de58fafe883bde697a5"): "\u7a3c\u5c3d\u53ef\u80fd\u65e5",
    bytes.fromhex("e7a8bce5838de78ab6e6b381"): "\u7a3c\u5c3d\u72b6\u6cc1",
    bytes.fromhex("e99da2e8ab87e5b88ce69c9b"): "\u9762\u8ac7\u5e0c\u671b",
}

new_raw = raw
replaced = []
not_found = []
for old_bytes, correct_str in prop_map.items():
    correct_bytes = correct_str.encode("utf-8")
    if old_bytes in new_raw:
        new_raw = new_raw.replace(old_bytes, correct_bytes)
        replaced.append(correct_str)
    else:
        not_found.append(correct_str)

with open(fpath, "wb") as f:
    f.write(new_raw)

sys.stdout.buffer.write(
    ("Done. replaced=" + str(len(replaced)) + " not_found=" + str(len(not_found)) + "\n").encode("utf-8")
)
sys.stdout.buffer.write(b"Replaced:\n")
for s in replaced:
    sys.stdout.buffer.write(("  " + s + "\n").encode("utf-8"))
sys.stdout.buffer.write(b"Not found:\n")
for s in not_found:
    sys.stdout.buffer.write(("  " + s + "\n").encode("utf-8"))

# UTF-8検証
with open(fpath, "rb") as f:
    verify = f.read().decode("utf-8")
sys.stdout.buffer.write(b"UTF-8 decode: OK\n")

# スキルフィルタ・ステータスフィルタの確認
checks = [
    "\u30b9\u30c6\u30fc\u30bf\u30b9",
    "\u5fc5\u8981\u30b9\u30ad\u30eb",
    "\u5355\u4fa1\uff08\u4e07\u5186\uff09",
    "\u62c5\u5f53\u8005",
]
for c in checks:
    found = c in verify
    sys.stdout.buffer.write(("  " + c + ": " + ("FOUND" if found else "MISSING") + "\n").encode("utf-8"))
