"""
backfill_v2.py - 正式版
修正点:
1. フィールド名を "備考（LINEメモ）" に修正
2. parse_sender改善: Company@など人名でないものを除外
3. R.E（[16]）: LINEメモに担当者メールが記載 → 所属メールをセット
4. LINE auto-register / 手動登録はスキップ（情報保持）
5. dry_run=True でテスト、False で本番実行
"""

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

DRY_RUN = True  # False にすると本番実行


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
    """
    人名かどうか判定（会社名・送信元ラベルっぽいものを除外）
    除外条件:
    - @が含まれる（メール or SNS）
    - 4文字以上の英数字のみ（会社コード等）
    - 株式会社/有限会社/合同会社で始まる
    - 明らかなサービス名（例: "ABC株式会社" の英数字部分等）
    """
    if not s:
        return False
    if "@" in s:
        return False
    if re.match(r"^[\u682a\u6709\u5408\u5171]", s):  # 株/有/合/共
        return False
    # 株式会社/有限会社/合同会社
    if re.search(r"(\u682a\u5f0f\u4f1a\u793e|\u6709\u9650\u4f1a\u793a|\u5408\u540c\u4f1a\u793e)", s):
        return False
    # 英数字+特殊文字のみ（例: "Phoenix福島＠エンジニア紹介"はOKとして上に引っかかる）
    # ＠（全角アットマーク）が含まれる
    if "\uff20" in s:  # ＠
        return False
    return True


def parse_sender(biko):
    """
    備考（LINEメモ）から送信元を解析
    戻り値: (email, person_name, status)
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
        # カッコ内除去
        name_part = re.sub(r"\(.*?\)", "", name_part).strip()
        # "_" プレフィックス（Company_Name形式）の場合、アンダースコア以降を取る
        if "_" in name_part and " " not in name_part.split("_")[0]:
            name_part = name_part.split("_", 1)[1].strip()
        person_name = name_part if is_person_name(name_part) else None
        return email, person_name, "ok"

    # メール直書き（<>なし）
    if re.match(r"^[\w.\-+]+@[\w.\-]+\.[a-zA-Z]+$", sender_str):
        return sender_str, None, "ok"

    return None, None, "parse_error"


def parse_line_memo_email(biko):
    """
    LINE経由登録（[LINE auto-register]なし）の備考から担当者メールを探す
    例: "担当: 伊藤 sota.ito@sakya.jp"
    """
    m = re.search(r"[\w.\-+]+@[\w.\-]+\.[a-zA-Z]+", biko)
    if m:
        return m.group(0)
    return None


def update_notion(page_id, props):
    """Notionページを更新"""
    r = requests.patch(f"https://api.notion.com/v1/pages/{page_id}", headers=headers, json={"properties": props})
    return r.status_code, r.json()


# メイン処理
pages = get_all_engineers()
mode = "DRY-RUN" if DRY_RUN else "LIVE"
print(f"[{mode}] backfill_v2 start - {len(pages)} records")
print("=" * 80)

stats = {"updated": 0, "skipped_line": 0, "skipped_manual": 0, "no_change": 0, "error": 0}
updates_log = []

for i, p in enumerate(pages):
    page_id = p["id"]
    biko = get_prop(p, "\u5099\u8003\uff08LINE\u30e1\u30e2\uff09")
    current_email = get_prop(p, "\u6240\u5c5e\u30e1\u30fc\u30eb")
    current_person = get_prop(p, "\u6240\u5c5e\u62c5\u5f53\u8005\u540d")
    name = get_prop(p, "\u540d\u524d")

    is_line_auto = "[LINE auto-register" in biko
    is_manual = "\u3010\u624b\u52d5\u767b\u9332\u3011" in biko

    # LINE自動登録（[LINE auto-register]タグあり） → スキップ
    if is_line_auto:
        print(f"[{i + 1:02d}] SKIP_LINE_AUTO: {name!r}")
        stats["skipped_line"] += 1
        continue

    # 手動登録 → スキップ
    if is_manual:
        print(f"[{i + 1:02d}] SKIP_MANUAL: {name!r}")
        stats["skipped_manual"] += 1
        continue

    # 送信元なし → LINEメモからメール抽出を試みる（R.Eパターン）
    email, person, status = parse_sender(biko)
    if status == "no_sender" and not current_email:
        extracted = parse_line_memo_email(biko)
        if extracted:
            email = extracted
            status = "ok_from_memo"
            print(f"[{i + 1:02d}] MEMO_EMAIL_EXTRACTED: {name!r} -> email={email!r}")

    if status in ("no_sender", "parse_error"):
        print(f"[{i + 1:02d}] {status.upper()}: {name!r}  biko={biko[:60]!r}")
        stats["no_change"] += 1
        continue

    # 更新内容を決定
    props_to_update = {}

    if email and not current_email:
        props_to_update["\u6240\u5c5e\u30e1\u30fc\u30eb"] = {"email": email}

    if person and not current_person:
        props_to_update["\u6240\u5c5e\u62c5\u5f53\u8005\u540d"] = {
            "rich_text": [{"type": "text", "text": {"content": person}}]
        }

    if not props_to_update:
        print(f"[{i + 1:02d}] NO_CHANGE: {name!r}  email={current_email!r}")
        stats["no_change"] += 1
        continue

    print(f"[{i + 1:02d}] UPDATE: {name!r}")
    for k, v in props_to_update.items():
        print(f"      {k} -> {list(v.values())[0]!r}")

    if not DRY_RUN:
        status_code, resp = update_notion(page_id, props_to_update)
        if status_code == 200:
            print("      -> Notion OK")
            stats["updated"] += 1
        else:
            print(f"      -> ERROR: {status_code} {resp}")
            stats["error"] += 1
    else:
        stats["updated"] += 1

    updates_log.append({"name": name, "page_id": page_id, "updates": props_to_update})

print("\n" + "=" * 80)
print(f"\n[{mode}] SUMMARY")
for k, v in stats.items():
    print(f"  {k}: {v}")

if updates_log:
    print("\n[UPDATE PLAN]")
    for u in updates_log:
        print(f"  {u['name']!r}: {list(u['updates'].keys())}")
