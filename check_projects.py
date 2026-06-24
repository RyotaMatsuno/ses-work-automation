import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
key = config.get("NOTION_API_KEY", "")
db = "343450ff-37c0-81e4-934e-f25f90284a3c"
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

all_results = []
cursor = None
while True:
    payload = {"page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor
    r = requests.post(f"https://api.notion.com/v1/databases/{db}/query", headers=headers, json=payload)
    data = r.json()
    all_results.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    cursor = data["next_cursor"]


def get_status(props):
    for key in ["Status", "\u30b9\u30c6\u30fc\u30bf\u30b9"]:
        v = props.get(key)
        if v and isinstance(v, dict):
            sel = v.get("select")
            if sel and isinstance(sel, dict):
                return sel.get("name", "unknown")
    return "unknown"


status_counts = {}
for p in all_results:
    props = p.get("properties", {})
    s = get_status(props)
    status_counts[s] = status_counts.get(s, 0) + 1

lines = [f"TOTAL={len(all_results)}"]
for k, v in sorted(status_counts.items(), key=lambda x: -x[1]):
    lines.append(f"{k}: {v}")

lines.append("")
lines.append("--- req skill projects ---")
for p in all_results:
    props = p.get("properties", {})
    name = props.get("\u6848\u4ef6\u540d", {}).get("title", [{}])
    name_str = name[0].get("plain_text", "") if name else ""
    s = get_status(props)
    req = [o["name"] for o in props.get("\u5fc5\u8981\u30b9\u30ad\u30eb", {}).get("multi_select", [])]
    if req:
        lines.append(f"{name_str} / {s} / {req}")

with open("proj_status.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("DONE")
