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


def parse_sender(biko):
    """
    備考（LINEメモ）から送信元メール・担当者名を抽出
    """
    m = re.search(r"\u9001\u4fe1\u5143[::\uff1a]\s*(.+?)(?:\n|$)", biko)
    if not m:
        return None, None, "no_sender"

    sender_str = m.group(1).strip()

    # <email> パターン
    email_m = re.search(r"<([^>]+@[^>]+)>", sender_str)
    if email_m:
        email = email_m.group(1).strip()
        name_part = sender_str[: email_m.start()].strip()
        # カッコ内除去（会社名等）
        name_part = re.sub(r"\(.*?\)", "", name_part).strip()
        # "Company_Name" 形式 → "Name" だけ取る（Company_が先頭にある場合）
        if "_" in name_part:
            parts = name_part.split("_", 1)
            if len(parts) == 2 and " " not in parts[0]:
                name_part = parts[1].strip()
        person_name = name_part if name_part else None
        return email, person_name, "ok"

    # メール直書き（<>なし）
    if re.match(r"^[\w.\-+]+@[\w.\-]+\.[a-zA-Z]+$", sender_str):
        return sender_str, None, "ok"

    return None, None, "parse_error"


pages = get_all_engineers()
print(f"Total: {len(pages)} records")
print("=" * 80)
print("\n[DRY-RUN: Parse Results for ALL records]")

stats = {
    "will_update_email": 0,
    "will_update_person": 0,
    "already_filled": 0,
    "line_auto": 0,
    "manual_reg": 0,
    "parse_error": 0,
}

for i, p in enumerate(pages):
    biko = get_prop(p, "\u5099\u8003\uff08LINE\u30e1\u30e2\uff09")
    current_email = get_prop(p, "\u6240\u5c5e\u30e1\u30fc\u30eb")
    current_person = get_prop(p, "\u6240\u5c5e\u62c5\u5f53\u8005\u540d")
    name = get_prop(p, "\u540d\u524d")

    email, person, status = parse_sender(biko)

    is_line_auto = "[LINE auto-register" in biko
    is_manual = "\u3010\u624b\u52d5\u767b\u9332\u3011" in biko

    # ステータス判定
    if is_line_auto:
        action = "SKIP_LINE_AUTO (保持)"
        stats["line_auto"] += 1
    elif is_manual:
        action = "SKIP_MANUAL (保持)"
        stats["manual_reg"] += 1
    elif status == "parse_error":
        action = "PARSE_ERROR"
        stats["parse_error"] += 1
    elif status == "no_sender":
        action = "NO_SENDER"
    else:
        # 更新するか判定
        actions = []
        if email and not current_email:
            actions.append(f"SET_EMAIL={email}")
            stats["will_update_email"] += 1
        elif email and current_email:
            match = "SAME" if email == current_email else f"DIFF(current={current_email})"
            actions.append(f"EMAIL_{match}")
            stats["already_filled"] += 1
        if person and not current_person:
            actions.append(f"SET_PERSON={person}")
            stats["will_update_person"] += 1
        action = " | ".join(actions) if actions else "NO_CHANGE"

    print(f"\n[{i + 1:02d}] {name!r}")
    print(f"      action={action}")
    print(f"      parsed: email={email!r} person={person!r}")
    print(f"      current: email={current_email!r} person={current_person!r}")
    if status in ("no_sender", "parse_error") and not is_line_auto and not is_manual:
        print(f"      biko_snippet={biko[:100]!r}")

print("\n" + "=" * 80)
print("\n[SUMMARY]")
for k, v in stats.items():
    print(f"  {k}: {v}")
