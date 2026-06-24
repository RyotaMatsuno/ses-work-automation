import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
import requests
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

DRY_RUN = False  # 本番実行


def get_all_engineers():
    results = []
    cursor = None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        r = requests.post(f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query", headers=headers, json=payload)
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return results


def get_prop(page, name):
    p = page["properties"].get(name, {})
    t = p.get("type", "")
    if t == "title":
        return "".join(i.get("plain_text", "") for i in p.get("title", []))
    elif t == "rich_text":
        return "".join(i.get("plain_text", "") for i in p.get("rich_text", []))
    elif t == "email":
        return p.get("email") or ""
    return ""


def is_person_name(s):
    if not s:
        return False
    if "@" in s:
        return False
    if "\uff20" in s:
        return False  # ＠
    if re.search(r"(\u682a\u5f0f\u4f1a\u793e|\u6709\u9650\u4f1a\u793a|\u5408\u540c\u4f1a\u793e)", s):
        return False
    return True


def parse_sender(biko):
    m = re.search(r"\u9001\u4fe1\u5143[::\uff1a]\s*(.+?)(?:\n|$)", biko)
    if not m:
        return None, None, "no_sender"
    sender_str = m.group(1).strip()
    email_m = re.search(r"<([^>]+@[^>]+)>", sender_str)
    if email_m:
        email = email_m.group(1).strip()
        name_part = sender_str[: email_m.start()].strip()
        name_part = re.sub(r"\(.*?\)", "", name_part).strip()
        if "_" in name_part and " " not in name_part.split("_")[0]:
            name_part = name_part.split("_", 1)[1].strip()
        person_name = name_part if is_person_name(name_part) else None
        return email, person_name, "ok"
    if re.match(r"^[\w.\-+]+@[\w.\-]+\.[a-zA-Z]+$", sender_str):
        return sender_str, None, "ok"
    return None, None, "parse_error"


def parse_line_memo_email(biko):
    m = re.search(r"[\w.\-+]+@[\w.\-]+\.[a-zA-Z]+", biko)
    return m.group(0) if m else None


def update_notion(page_id, props):
    r = requests.patch(f"https://api.notion.com/v1/pages/{page_id}", headers=headers, json={"properties": props})
    return r.status_code, r.json()


pages = get_all_engineers()
stats = {"updated": 0, "skipped_line": 0, "skipped_manual": 0, "no_change": 0, "error": 0}

for i, p in enumerate(pages):
    page_id = p["id"]
    biko = get_prop(p, "\u5099\u8003\uff08LINE\u30e1\u30e2\uff09")
    current_email = get_prop(p, "\u6240\u5c5e\u30e1\u30fc\u30eb")
    current_person = get_prop(p, "\u6240\u5c5e\u62c5\u5f53\u8005\u540d")
    name = get_prop(p, "\u540d\u524d")

    is_line_auto = "[LINE auto-register" in biko
    is_manual = "\u3010\u624b\u52d5\u767b\u9332\u3011" in biko

    if is_line_auto:
        stats["skipped_line"] += 1
        continue
    if is_manual:
        stats["skipped_manual"] += 1
        continue

    email, person, status = parse_sender(biko)
    if status == "no_sender" and not current_email:
        extracted = parse_line_memo_email(biko)
        if extracted:
            email = extracted
            status = "ok_from_memo"

    if status in ("no_sender", "parse_error"):
        stats["no_change"] += 1
        continue

    props_to_update = {}
    if email and not current_email:
        props_to_update["\u6240\u5c5e\u30e1\u30fc\u30eb"] = {"email": email}
    if person and not current_person:
        props_to_update["\u6240\u5c5e\u62c5\u5f53\u8005\u540d"] = {
            "rich_text": [{"type": "text", "text": {"content": person}}]
        }
    if not props_to_update:
        stats["no_change"] += 1
        continue

    status_code, resp = update_notion(page_id, props_to_update)
    if status_code == 200:
        print(f"UPDATED [{i + 1:02d}] {name!r}: {list(props_to_update.keys())}")
        stats["updated"] += 1
    else:
        print(f"ERROR [{i + 1:02d}] {name!r}: {status_code} {resp.get('message', '')}")
        stats["error"] += 1

print("\n[LIVE] SUMMARY")
for k, v in stats.items():
    print(f"  {k}: {v}")
