import datetime
import json
import urllib.request
from collections import Counter

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_API_KEY")
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

two_days_ago = (
    datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))) - datetime.timedelta(days=2)
).strftime("%Y-%m-%dT%H:%M:%S+09:00")

payload = {"page_size": 100, "filter": {"timestamp": "created_time", "created_time": {"after": two_days_ago}}}
pages = []
cursor = None
while True:
    if cursor:
        payload["start_cursor"] = cursor
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"https://api.notion.com/v1/databases/{PROJECT_DB}/query",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        res = json.loads(r.read())
    pages.extend(res.get("results", []))
    if not res.get("has_more"):
        break
    cursor = res.get("next_cursor")

# 案件名で重複チェック
titles = []
for p in pages:
    title_parts = p["properties"].get("案件名", {}).get("title", [])
    title = "".join(t.get("plain_text", "") for t in title_parts).strip()
    titles.append(title)

# 完全一致
exact_counter = Counter(titles)
unique_exact = len(exact_counter)
dupes_exact = sum(1 for v in exact_counter.values() if v > 1)

# 正規化（空白・記号除去）して類似判定
import re


def normalize(t):
    t = re.sub(r"[\s\u3000【】\[\]（）()「」・/／]", "", t)
    t = t.lower()
    return t


norm_counter = Counter(normalize(t) for t in titles if t)
unique_norm = len(norm_counter)
dupes_norm = sum(1 for v in norm_counter.values() if v > 1)

# 最も重複が多い案件
top_dupes = norm_counter.most_common(10)

print(f"2日以内の案件: {len(pages)}件")
print("\n=== 重複分析 ===")
print(f"案件名 完全一致ユニーク: {unique_exact}件 (重複{len(pages) - unique_exact}件)")
print(f"案件名 正規化後ユニーク: {unique_norm}件 (重複{len(pages) - unique_norm}件)")
print(f"重複率: {(1 - unique_norm / len(pages)) * 100:.1f}%")

print("\n=== 重複トップ10 ===")
for title, cnt in top_dupes:
    print(f"  {cnt}回: {title[:60]}")
