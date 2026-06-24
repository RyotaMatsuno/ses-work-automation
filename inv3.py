import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_TOKEN") or config.get("NOTION_API_KEY")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# 入力元フィールドのhex確認
inp_hex = "入力元".encode("utf-8").hex()
print(f"入力元 hex: {inp_hex}")
print(f"decode確認: {bytes.fromhex(inp_hex).decode()}")
print()

# H.S エンジニアレコードの入力元確認
r = requests.get("https://api.notion.com/v1/pages/36c450ff-37c0-813b-8f31-d38228e3cf2e", headers=headers, timeout=10)
props = r.json().get("properties", {})
input_src_eng = (props.get("入力元", {}).get("select") or {}).get("name", "")
memo = "".join(t.get("plain_text", "") for t in props.get("備考（LINEメモ）", {}).get("rich_text", []))
print(f"H.S 入力元フィールド: [{input_src_eng}]")
print(f"H.S 備考先頭: [{memo[:60]}]")
print()

# 上位5案件の入力元確認
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
for m in list(sys.modules):
    if "line_query" in m:
        del sys.modules[m]
from line_query import (
    PROJECT_DB_ID,
    PROP_ASSIGNEE,
    PROP_PJDETAIL,
    PROP_PJNAME,
    PROP_RATE,
    PROP_REQSK,
    PROP_STATUS,
    VAL_RECRUITING,
    _multi_select_prop,
    _number_prop,
    _select_prop,
    _text_prop,
    business_days_since,
    calc_gross_profit,
    fetch_all_pages,
    skill_match,
)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
SENDER_RE = re.compile(r"(?:送信元|送信者)[:\s：]+(.{1,80}?)(?:\s*/\s*受信日|$)", re.DOTALL)

prj_filter = {
    "and": [
        {"property": PROP_STATUS, "select": {"equals": VAL_RECRUITING}},
        {"property": PROP_RATE, "number": {"greater_than": 0}},
    ]
}
pages = fetch_all_pages(PROJECT_DB_ID, filter_body=prj_filter)

hs_skills = ["Java", "JavaScript", "SQL Server", "Oracle", "Spring", "C#"]
hs_rate = 70.0

seen = set()
deduped = []
for p in pages:
    k = _text_prop(p, PROP_PJNAME)[:20]
    if k and k not in seen:
        seen.add(k)
        deduped.append(p)

matched = []
for p in deduped:
    if business_days_since(p.get("last_edited_time")) > 4:
        continue
    req = _multi_select_prop(p, PROP_REQSK)
    if not req:
        continue
    if not skill_match(req, hs_skills):
        continue
    budget = _number_prop(p, PROP_RATE)
    if budget > 150:
        continue
    gross = calc_gross_profit(budget, hs_rate)
    thresh = 5 if _select_prop(p, PROP_ASSIGNEE) == "松野" else 3
    if gross < thresh:
        continue
    matched.append(p)

matched.sort(key=lambda x: _number_prop(x, PROP_RATE), reverse=True)

print("=== 上位5案件の入力元・送信元 ===")
for i, p in enumerate(matched[:5], 1):
    name = _text_prop(p, PROP_PJNAME)
    # 入力元フィールド
    input_src = (p.get("properties", {}).get("入力元", {}).get("select") or {}).get("name", "")
    # 案件詳細から送信元
    detail = _text_prop(p, PROP_PJDETAIL)
    sender_m = SENDER_RE.search(detail) if detail else None
    sender_raw = sender_m.group(1).strip() if sender_m else ""
    email_m = EMAIL_RE.search(sender_raw) if sender_raw else None
    domain = email_m.group(0).split("@")[1] if email_m else ""
    before = sender_raw[: sender_raw.find(email_m.group(0))].strip().rstrip("<").strip() if email_m else ""

    print(f"  [{i}] {name[:35]}")
    print(f"       入力元フィールド: [{input_src}]")
    print(f"       送信者名: [{before[:30]}]")
    print(f"       メール: [{email_m.group(0) if email_m else ''}]")
    print(f"       ドメイン: [{domain}]")
    print()
