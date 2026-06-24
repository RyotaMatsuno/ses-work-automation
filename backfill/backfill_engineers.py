# -*- coding: utf-8 -*-
"""
backfill_engineers.py
Backfill missing fields (イニシャル / 所属メール / 所属担当者名) in Notion Engineer DB.
Source: 備考（LINEメモ）field which contains "送信元: ..." line.
"""

import argparse
import os
import re
import time

import requests
from dotenv import dotenv_values

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
NOTION_VERSION = "2022-06-28"
LOG_FILE = os.path.join(BASE_DIR, "backfill_log.txt")

# Load .env from ses_work/config/.env
config = dotenv_values(os.path.join(BASE_DIR, "..", "config", ".env"))
NOTION_API_KEY = config.get("NOTION_API_KEY", "")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}

# Regex patterns
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
ANGLE_EMAIL_RE = re.compile(r"<\s*([^<>\s]+@[^<>\s]+)\s*>")
SENDER_RE = re.compile(r"^\s*\u9001\u4fe1\u5143:\s*(.+)\s*$", re.MULTILINE)

INITIAL_DOT_RE = re.compile(r"^[A-Z]\.[A-Z]$")
INITIAL_PLAIN_RE = re.compile(r"^[A-Z]{2,3}$")
EXISTING_INITIAL_RE = re.compile(r"^[A-Z\s.]{2,6}$")
SKILL_CODE_RE = re.compile(r"^(?=.*\d)(?=.*[A-Za-z])[A-Za-z0-9]{4,}$")
SHORT_ASCII_RE = re.compile(r"^[A-Z]{1,3}$")

# Company detection: katakana or common corp keywords
COMPANY_KEYWORDS = [
    "\u682a\u5f0f\u4f1a\u793e",
    "\u5408\u540c\u4f1a\u793e",
    "Inc",
    "Corp",
    "Ltd",
    "LLC",
    "\u30a8\u30f3\u30b8\u30cb\u30a2",
    "\u30c6\u30c3\u30af",
    "\u30ea\u30f3\u30af",
    "\u30bd\u30ea\u30e5\u30fc\u30b7\u30e7\u30f3",
]


def log_line(message):
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    # Print as-is (stdout may be utf-8 or cp932)
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        print(message.encode("ascii", "replace").decode(), flush=True)


def rich_text_value(prop):
    return "".join(item.get("plain_text", "") for item in prop.get("rich_text", []))


def title_value(prop):
    return "".join(item.get("plain_text", "") for item in prop.get("title", []))


def email_prop_value(prop):
    return prop.get("email") or ""


def is_empty_rich_text(props, field_name):
    prop = props.get(field_name, {})
    return not rich_text_value(prop).strip()


def is_empty_email(props, field_name):
    prop = props.get(field_name, {})
    return not email_prop_value(prop).strip()


def fetch_target_records():
    """Fetch records where all 3 fields are empty."""
    filter_obj = {
        "and": [
            {"property": "\u30a4\u30cb\u30b7\u30e3\u30eb", "rich_text": {"is_empty": True}},
            {"property": "\u6240\u5c5e\u30e1\u30fc\u30eb", "email": {"is_empty": True}},
            {"property": "\u6240\u5c5e\u62c5\u5f53\u8005\u540d", "rich_text": {"is_empty": True}},
        ]
    }
    payload = {"page_size": 100, "filter": filter_obj}
    results = []
    while True:
        response = requests.post(
            f"https://api.notion.com/v1/databases/{DB_ID}/query",
            headers=HEADERS,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    return results


def looks_like_company(text):
    candidate = text.strip()
    if not candidate:
        return False
    if any(kw in candidate for kw in COMPANY_KEYWORDS):
        return True
    if re.fullmatch(r"[A-Z]+", candidate):
        return True
    if " " not in candidate and "." in candidate:
        return True
    # katakana
    if re.search(r"[\u30a0-\u30ff]", candidate):
        return True
    return False


def extract_email(sender):
    angle_match = ANGLE_EMAIL_RE.search(sender)
    if angle_match:
        email_match = EMAIL_RE.search(angle_match.group(1))
        return email_match.group(0) if email_match else None
    email_match = EMAIL_RE.search(sender)
    return email_match.group(0) if email_match else None


def extract_person_name(sender):
    angle_index = sender.find("<")
    if angle_index < 0:
        return None
    before_angle = sender[:angle_index].strip().strip('"').strip("'")
    if not before_angle:
        return None
    # Remove company name in parens: "Name(Company)<email>"
    paren_match = re.match(r"^(.*?)\s*[\(\uff08][^\)\uff09]+[\)\uff09]\s*$", before_angle)
    if paren_match:
        before_angle = paren_match.group(1).strip()
    if not before_angle or looks_like_company(before_angle):
        return None
    return before_angle


def parse_sender(note_text):
    match = SENDER_RE.search(note_text or "")
    if not match:
        return None, None, "NO_SENDER"
    sender = match.group(1).strip()
    email = extract_email(sender)
    person_name = extract_person_name(sender)
    status = "OK" if (email or person_name) else "NO_VALUES"
    return email, person_name, status


def generate_initial(name):
    value = (name or "").strip()
    if not value:
        return None, "NO_NAME"
    if INITIAL_DOT_RE.fullmatch(value) or INITIAL_PLAIN_RE.fullmatch(value):
        return value, "EXISTING_INITIAL"
    if EXISTING_INITIAL_RE.fullmatch(value):
        return value, "EXISTING_INITIAL"
    if SKILL_CODE_RE.fullmatch(value):
        return None, "SKIP_CODE"
    if SHORT_ASCII_RE.fullmatch(value):
        return value, "SHORT_ASCII"
    # Contains non-ASCII (Japanese) -> skip
    if re.search(r"[^\x00-\x7f]", value):
        return None, "NEEDS_MANUAL"
    # ASCII with space -> try initials
    if " " in value:
        parts = [p for p in value.split() if p]
        initials = [p[0].upper() for p in parts if re.match(r"^[A-Za-z]", p)]
        if len(initials) >= 2:
            return ".".join(initials[:2]), "ASCII_NAME"
    return None, "UNSUPPORTED_NAME"


def build_patch_payload(props, initial, email, person_name):
    properties = {}
    if initial and is_empty_rich_text(props, "\u30a4\u30cb\u30b7\u30e3\u30eb"):
        properties["\u30a4\u30cb\u30b7\u30e3\u30eb"] = {"rich_text": [{"text": {"content": initial}}]}
    if email and is_empty_email(props, "\u6240\u5c5e\u30e1\u30fc\u30eb"):
        properties["\u6240\u5c5e\u30e1\u30fc\u30eb"] = {"email": email}
    if person_name and is_empty_rich_text(props, "\u6240\u5c5e\u62c5\u5f53\u8005\u540d"):
        properties["\u6240\u5c5e\u62c5\u5f53\u8005\u540d"] = {"rich_text": [{"text": {"content": person_name}}]}
    return {"properties": properties} if properties else None


def patch_notion_page(page_id, payload):
    response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )
    time.sleep(0.3)
    if response.status_code >= 400:
        return False, f"{response.status_code}: {response.text[:300]}"
    return True, "OK"


def summarize_payload(payload):
    if not payload:
        return "none"
    values = []
    props = payload.get("properties", {})
    if "\u30a4\u30cb\u30b7\u30e3\u30eb" in props:
        v = props["\u30a4\u30cb\u30b7\u30e3\u30eb"]["rich_text"][0]["text"]["content"]
        values.append(f"initial={v}")
    if "\u6240\u5c5e\u30e1\u30fc\u30eb" in props:
        values.append(f"email={props[chr(0x6240) + chr(0x5C5E) + chr(0x30E1) + chr(0x30FC) + chr(0x30EB)]['email']}")
    if "\u6240\u5c5e\u62c5\u5f53\u8005\u540d" in props:
        v = props["\u6240\u5c5e\u62c5\u5f53\u8005\u540d"]["rich_text"][0]["text"]["content"]
        values.append(f"person={v}")
    return ", ".join(values) if values else "none"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if not NOTION_API_KEY:
        raise RuntimeError("NOTION_API_KEY is not set in config/.env")

    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"\n=== start dry_run={args.dry_run} ===\n")

    records = fetch_target_records()
    if args.limit > 0:
        records = records[: args.limit]

    total = len(records)
    updated = 0
    skipped = 0
    errors = 0

    log_line(f"START total={total} dry_run={args.dry_run}")

    for index, page in enumerate(records, start=1):
        page_id = page.get("id", "")
        props = page.get("properties", {})
        name = title_value(props.get("\u540d\u524d", {}))
        note = rich_text_value(props.get("\u5099\u8003\uff08LINE\u30e1\u30e2\uff09", {}))

        email, person_name, sender_status = parse_sender(note)
        initial, initial_status = generate_initial(name)
        payload = build_patch_payload(props, initial, email, person_name)
        values = summarize_payload(payload)

        if not payload:
            skipped += 1
            log_line(
                f"{index}/{total} SKIP page={page_id} name={name} "
                f"sender={sender_status} initial={initial_status} values={values}"
            )
            continue

        if args.dry_run:
            updated += 1
            log_line(
                f"{index}/{total} DRY_RUN page={page_id} name={name} "
                f"sender={sender_status} initial={initial_status} values={values}"
            )
            continue

        success, result = patch_notion_page(page_id, payload)
        if success:
            updated += 1
            log_line(f"{index}/{total} UPDATED page={page_id} name={name} values={values}")
        else:
            errors += 1
            log_line(f"{index}/{total} ERROR page={page_id} name={name} values={values} error={result}")

    summary = f"SUMMARY total={total} updated={updated} skipped={skipped} errors={errors} dry_run={args.dry_run}"
    log_line(summary)


if __name__ == "__main__":
    main()
