import sys, json, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values
cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
KEY = cfg.get("NOTION_API_KEY")
DB = "36c450ff-37c0-8180-be7c-c5587e6b8616"
H = {"Authorization": f"Bearer {KEY}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

out = []
out.append("=== USAGE TRACKER DB SCHEMA ===")
r = requests.get(f"https://api.notion.com/v1/databases/{DB}", headers=H, timeout=30)
out.append(f"status={r.status_code}")
if r.status_code == 200:
    props = r.json().get("properties", {})
    for name, p in props.items():
        out.append(f"  PROP: {name} ({p.get('type')})")
else:
    out.append(r.text[:500])

out.append("\n=== ROWS (paginated) ===")
rows = []
cursor = None
while True:
    body = {"page_size": 100}
    if cursor: body["start_cursor"] = cursor
    rr = requests.post(f"https://api.notion.com/v1/databases/{DB}/query", headers=H, json=body, timeout=60)
    if rr.status_code != 200:
        out.append(f"query status={rr.status_code} {rr.text[:300]}")
        break
    d = rr.json()
    rows.extend(d.get("results", []))
    if not d.get("has_more"): break
    cursor = d.get("next_cursor")

out.append(f"total_rows={len(rows)}")

# dump raw property values for the most recent ~40 rows to infer structure
def flat(props):
    o = {}
    for k, v in props.items():
        t = v.get("type")
        val = None
        if t == "title": val = "".join([x.get("plain_text","") for x in v.get("title",[])])
        elif t == "rich_text": val = "".join([x.get("plain_text","") for x in v.get("rich_text",[])])
        elif t == "number": val = v.get("number")
        elif t == "date": val = (v.get("date") or {}).get("start")
        elif t == "select": val = (v.get("select") or {}).get("name")
        elif t == "formula": val = v.get("formula")
        elif t == "created_time": val = v.get("created_time")
        else: val = str(v.get(t))[:60]
        o[k] = val
    return o

flatrows = [flat(x.get("properties",{})) for x in rows]
# sort by any date-ish field if present
for fr in flatrows[-50:]:
    out.append(json.dumps(fr, ensure_ascii=False))

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\_cost_audit_usage.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(str(x) for x in out))
print("DONE rows=", len(rows))
