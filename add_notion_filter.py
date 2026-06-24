import sys

fpath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(fpath, "rb") as f:
    raw = f.read()

# 1. fetch_all_pages に filter 引数を追加
old_fetch = b'def fetch_all_pages(db_id: str) -> list[dict]:\n\n\n\n    results: list[dict] = []\n\n\n\n    payload: dict[str, Any] = {"page_size": 100}'
new_fetch = b'def fetch_all_pages(db_id: str, filter_body: dict = None) -> list[dict]:\n\n\n\n    results: list[dict] = []\n\n\n\n    payload: dict[str, Any] = {"page_size": 100}\n\n\n\n    if filter_body:\n\n\n\n        payload["filter"] = filter_body'

if old_fetch in raw:
    raw = raw.replace(old_fetch, new_fetch)
    sys.stdout.buffer.write(b"fetch_all_pages updated\n")
else:
    sys.stdout.buffer.write(b"fetch_all_pages target not found\n")

# 2. engineer_query 内の fetch_all_pages(PROJECT_DB_ID) を
#    filter付き呼び出しに変更
# 単価(万円) >= 75 でNotionフィルタ
# PROP_RATE のhex = e58d98e4bea1efbc88e4b887e58686efbc89

old_fetch_prj = b"projects = fetch_all_pages(PROJECT_DB_ID)"

# 単価(万円)フィールド名をbytesで構築
prop_rate_bytes = bytes.fromhex("e58d98e4bea1efbc88e4b887e58686efbc89")

new_fetch_prj = (
    b'_prj_filter = {"and": ['
    b'{"property": "' + prop_rate_bytes + b'", "number": {"greater_than_or_equal_to": 75}},'
    b'{"property": "'
    + bytes.fromhex("e382b9e38386e383bce382bfe382b9")
    + b'", "select": {"equals": "'
    + bytes.fromhex("e58b9fe99b86e4b8ad")
    + b'"}}'
    b"]}\n\n\n        projects = fetch_all_pages(PROJECT_DB_ID, filter_body=_prj_filter)"
)

if old_fetch_prj in raw:
    raw = raw.replace(old_fetch_prj, new_fetch_prj)
    sys.stdout.buffer.write(b"fetch projects with filter updated\n")
else:
    sys.stdout.buffer.write(b"fetch_projects target not found\n")

with open(fpath, "wb") as f:
    f.write(raw)

# 検証
with open(fpath, "rb") as f:
    v = f.read().decode("utf-8", errors="replace")
idx = v.find("_prj_filter")
sys.stdout.buffer.write(f"_prj_filter in file: {idx > 0}\n".encode())
sys.stdout.buffer.write(v[idx : idx + 200].encode("utf-8", errors="replace"))
