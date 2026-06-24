import sys

fpath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"

props = {
    "e382a4e3838be382b7e383a3e383ab": "PROP_INI",
    "e5908de5898d": "PROP_NAME",
    "e69c80e5af84e3828ae9a785": "PROP_STA",
    "e58299e88083efbc884c494e45e383a1e383a2efbc89": "PROP_MEMO",
    "e382b9e382ade383ab": "PROP_SKILL",
    "e58d98e4bea1efbc88e4b887e58686efbc89": "PROP_RATE",
    "e382b9e38386e383bce382bfe382b9": "PROP_STATUS",
    "e5bf85e8a681e382b9e382ade383ab": "PROP_REQSK",
    "e5b09ae58fafe382b9e382ade383ab": "PROP_OPTSK",
    "e68b85e5bd93e88085": "PROP_ASSIGNEE",
    "e6a188e4bbb6e5908d": "PROP_PJNAME",
    "e6a188e4bbb6e8a9b3e7b4b0": "PROP_PJDETAIL",
    "e383aae383a2e383bce38388": "PROP_REMOTE",
    "e58ba4e58b99e59cb0": "PROP_LOCATION",
    "e69c9fe99693": "PROP_PERIOD",
    "e99da2e8ab87e5b88ce69c9b": "PROP_INTERVIEW",
    "e7a8bce5838de58fafe883bde697a5": "PROP_WORKON",
    "e7a8bce5838de78ab6e6b381": "PROP_WORKST",
    "e68980e5b19ee4bc9ae7a4be": "PROP_AFFIL",
    "e5aea1e99b86e4b8ad": "VAL_RECRUITING",
}

with open(fpath, "rb") as f:
    raw = f.read()

new_raw = raw
total = 0
for hexval, const_name in props.items():
    key_bytes = bytes.fromhex(hexval)
    # "KEY" -> PROP_XXX / 'KEY' -> PROP_XXX の両パターン置換
    for quote in [b'"', b"'"]:
        old = quote + key_bytes + quote
        new = const_name.encode()
        if old in new_raw:
            cnt = new_raw.count(old)
            new_raw = new_raw.replace(old, new)
            total += cnt
            sys.stdout.buffer.write(f"  {const_name}: {cnt}x\n".encode())

# "募集中" も置換
bosku_bytes = bytes.fromhex("e5aea1e99b86e4b8ad")
for quote in [b'"', b"'"]:
    old = quote + bosku_bytes + quote
    new = b"VAL_RECRUITING"
    if old in new_raw:
        cnt = new_raw.count(old)
        new_raw = new_raw.replace(old, new)
        total += cnt
        sys.stdout.buffer.write(f"  VAL_RECRUITING(value): {cnt}x\n".encode())

with open(fpath, "wb") as f:
    f.write(new_raw)

sys.stdout.buffer.write(f"Total: {total} replacements\n".encode())

# 検証: engineer_query 内
with open(fpath, "rb") as f:
    v = f.read().decode("utf-8")
idx = v.find("def engineer_query")
nxt = v.find("\ndef project_query")
eq = v[idx:nxt]
# 化けた文字が残っていないか確認
bad = [c for c in eq if ord(c) > 0x2000 and c not in "イニシャルスキルステータス募集中必要尚可担当者単価万円"]
sys.stdout.buffer.write(f"Non-ASCII suspicious chars in engineer_query: {len(bad)}\n".encode())
# PROP_XXX 参照が入っているか
for const in ["PROP_SKILL", "PROP_STATUS", "VAL_RECRUITING", "PROP_REQSK", "PROP_RATE", "PROP_ASSIGNEE"]:
    sys.stdout.buffer.write(f"  {const} in eq: {const in eq}\n".encode())
