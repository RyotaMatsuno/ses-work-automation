"""
過去3週間のsessalesメール全件をNotionに一括登録するスクリプト
"""

import email
import imaplib
import json
import os
import re
from datetime import datetime, timedelta
from email.header import decode_header

import requests
from dotenv import dotenv_values

# .envロード
env_path = os.path.join(os.path.dirname(__file__), "config", ".env")
config = dotenv_values(env_path)
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v

IMAP_SERVER = os.environ.get("OUTLOOK_IMAP_SERVER", "mail65.onamae.ne.jp")
IMAP_PORT = int(os.environ.get("OUTLOOK_IMAP_PORT", "993"))
EMAIL_USER = os.environ.get("OUTLOOK_EMAIL", "")
EMAIL_PASS = os.environ.get("OUTLOOK_PASSWORD", "")

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_ENGINEER_DB_ID = os.environ.get("NOTION_ENGINEER_DB_ID", "")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

VALID_SKILLS = ["Java", "Python", "PHP", "JavaScript", "TypeScript", "C#", "Node.js", "React", "AWS", "インフラ"]

# 人材情報の判定キーワード（3軸）
SKILL_KEYWORDS = [
    "Java",
    "Python",
    "PHP",
    "JavaScript",
    "TypeScript",
    "C#",
    "Node.js",
    "Node ",
    "React",
    "AWS",
    "インフラ",
    "Linux",
    "ネットワーク",
    "プログラマ",
    "エンジニア",
    "要員",
    "技術者",
]
PRICE_KEYWORDS = [
    "単価",
    "希望単価",
    "月額",
    "/月",
    "万円",
    "万/月",
]
START_KEYWORDS = [
    "稼働可能",
    "参画可能",
    "開始時期",
    "入場可能",
    "稼働日",
    "即日",
    "翌月",
    "来月から",
    "稼働開始",
]


def decode_str(s):
    if s is None:
        return ""
    parts = decode_header(s)
    result = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            result += part.decode(enc or "utf-8", errors="ignore")
        else:
            result += str(part)
    return result


def get_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                charset = part.get_content_charset() or "utf-8"
                try:
                    body = part.get_payload(decode=True).decode(charset, errors="ignore")
                    if body.strip():
                        break
                except:
                    pass
        if not body:
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/html":
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        html = part.get_payload(decode=True).decode(charset, errors="ignore")
                        body = re.sub(r"<[^>]+>", " ", html)
                        body = re.sub(r"&nbsp;", " ", body)
                        body = re.sub(r"\s+", " ", body).strip()
                        break
                    except:
                        pass
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            body = msg.get_payload(decode=True).decode(charset, errors="ignore")
        except:
            body = str(msg.get_payload())
    return body.strip()


def is_engineer_email(subject, body):
    """単価・スキル・開始時期のいずれかが含まれるメールのみ人材情報と判定"""
    text = f"{subject} {body[:800]}"
    has_skill = any(kw in text for kw in SKILL_KEYWORDS)
    has_price = any(kw in text for kw in PRICE_KEYWORDS)
    has_start = any(kw in text for kw in START_KEYWORDS)
    # 3軸のうち2つ以上、またはスキルが含まれていれば人材情報とみなす
    matched = sum([has_skill, has_price, has_start])
    return matched >= 2 or (has_skill and (has_price or has_start))


def parse_info(subject, body, sender):
    text = f"{subject}\n{body}"
    info = {}

    # 名前（複数パターン）
    for pat in [
        r"氏名[：:\s]*([^\s\n　]{2,8})",
        r"名前[：:\s]*([^\s\n　]{2,8})",
        r"お名前[：:\s]*([^\s\n　]{2,8})",
        r"候補者[：:\s]*([^\s\n　]{2,8})",
        r"エンジニア名[：:\s]*([^\s\n　]{2,8})",
    ]:
        m = re.search(pat, text)
        if m:
            info["name"] = m.group(1).strip()
            break

    # スキル
    skills = []
    skill_map = {
        "Java": r"\bJava\b(?!Script)",
        "Python": r"\bPython\b",
        "PHP": r"\bPHP\b",
        "JavaScript": r"\bJavaScript\b",
        "TypeScript": r"\bTypeScript\b",
        "C#": r"\bC#\b",
        "Node.js": r"\bNode\.?js\b",
        "React": r"\bReact\b",
        "AWS": r"\bAWS\b",
        "インフラ": r"インフラ|ネットワーク|Linux",
    }
    for skill, pat in skill_map.items():
        if re.search(pat, text, re.IGNORECASE):
            skills.append(skill)
    if skills:
        info["skills"] = skills

    # 単価
    for pat in [r"単価[：:\s]*(\d+)万?", r"希望単価[：:\s]*(\d+)", r"(\d+)万円?/月"]:
        m = re.search(pat, text)
        if m:
            p = int(m.group(1))
            if 30 <= p <= 200:
                info["price"] = p
                break

    # 経験年数
    for pat in [r"経験[：:\s]*(\d+)年", r"経験年数[：:\s]*(\d+)", r"(\d+)年経験"]:
        m = re.search(pat, text)
        if m:
            e = int(m.group(1))
            if 0 <= e <= 50:
                info["experience"] = e
                break

    # 稼働可能日
    for pat in [
        r"稼働可能日[：:\s]*(\d{4}年\d{1,2}月\d{1,2}日?)",
        r"稼働[：:\s]*(\d{4}年\d{1,2}月\d{1,2}日?)",
        r"参画可能[：:\s]*(\d{4}年\d{1,2}月\d{1,2}日?)",
    ]:
        m = re.search(pat, text)
        if m:
            ds = m.group(1)
            ds = re.sub(
                r"(\d{4})年(\d{1,2})月(\d{1,2})日?",
                lambda x: f"{x.group(1)}-{int(x.group(2)):02d}-{int(x.group(3)):02d}",
                ds,
            )
            if re.match(r"\d{4}-\d{2}-\d{2}", ds):
                info["available_date"] = ds[:10]
            break

    # メール
    em = re.search(r"[\w.\-+]+@[\w.\-]+\.\w{2,}", text)
    if em and em.group(0) != EMAIL_USER:
        info["email"] = em.group(0)

    # 電話
    tel = re.search(r"(\d{2,4}[-\s]?\d{2,4}[-\s]?\d{3,4})", text)
    if tel:
        info["tel"] = tel.group(1)

    return info


def register(info, subject, sender, date_str):
    name = info.get("name", f"【{subject[:20]}】")
    note = f"【Outlookから自動登録】\n受信日: {date_str}\n件名: {subject}\n送信者: {sender}\n\n"
    # 本文の一部も備考に
    note = note[:2000]

    props = {
        "名前": {"title": [{"text": {"content": name}}]},
        "稼働状況": {"select": {"name": "稼働可能"}},
        "備考（LINEメモ）": {"rich_text": [{"text": {"content": note}}]},
    }
    if "skills" in info and info["skills"]:
        props["スキル"] = {"multi_select": [{"name": s} for s in info["skills"] if s in VALID_SKILLS]}
    if "price" in info:
        props["単価（万円）"] = {"number": info["price"]}
    if "available_date" in info:
        props["稼働可能日"] = {"date": {"start": info["available_date"]}}
    if "experience" in info:
        props["経験年数"] = {"number": info["experience"]}
    if "tel" in info:
        props["連絡先"] = {"phone_number": info["tel"]}
    if "email" in info:
        props["メール"] = {"email": info["email"]}

    r = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": NOTION_ENGINEER_DB_ID}, "properties": props},
    )
    return r.status_code == 200


def main():
    print("=" * 60)
    print("過去3週間 sessalesメール → Notion 一括登録")
    print("=" * 60)
    print(f"接続先: {IMAP_SERVER}:{IMAP_PORT}")
    print(f"アカウント: {EMAIL_USER}")

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        print("✅ ログイン成功")
    except Exception as e:
        print(f"❌ 接続失敗: {e}")
        return

    # 利用可能なフォルダ一覧を確認
    _, folders = mail.list()
    print("\n📁 フォルダ一覧:")
    folder_list = []
    for f in folders[:15]:
        folder_list.append(f.decode("utf-8", errors="ignore"))
        print(f"  {folder_list[-1]}")

    # INBOXを選択
    mail.select("INBOX")

    since = (datetime.now() - timedelta(weeks=3)).strftime("%d-%b-%Y")
    print(f"\n🔍 検索: SINCE {since}")

    _, msgs = mail.search(None, f"SINCE {since}")
    ids = msgs[0].split()
    print(f"📧 対象メール: {len(ids)}件")

    registered = 0
    skipped = 0
    results = []

    for i, mid in enumerate(ids):
        try:
            _, data = mail.fetch(mid, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])

            subject = decode_str(msg.get("Subject", ""))
            sender = decode_str(msg.get("From", ""))
            date_s = msg.get("Date", "")
            body = get_body(msg)

            print(f"\n[{i + 1}/{len(ids)}] {subject[:45]}")
            print(f"  From: {sender[:45]}")

            if not is_engineer_email(subject, body):
                print("  → スキップ（人材情報キーワードなし）")
                skipped += 1
                continue

            info = parse_info(subject, body, sender)
            ok = register(info, subject, sender, date_s)

            if ok:
                print(
                    f"  ✅ 登録: {info.get('name', '名前未設定')} / スキル: {info.get('skills', [])} / 単価: {info.get('price', '-')}万"
                )
                registered += 1
                results.append(
                    {
                        "name": info.get("name", ""),
                        "subject": subject,
                        "sender": sender,
                        "skills": info.get("skills", []),
                        "price": info.get("price"),
                    }
                )
            else:
                print("  ❌ 登録失敗")
                skipped += 1

        except Exception as e:
            print(f"  ❌ 例外: {e}")
            skipped += 1
            continue

    mail.logout()

    print("\n" + "=" * 60)
    print(f"✅ 完了! 登録: {registered}件 / スキップ: {skipped}件 / 合計: {len(ids)}件")
    print("=" * 60)

    out = os.path.join(os.path.dirname(__file__), "import_result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(
            {"registered": registered, "skipped": skipped, "total": len(ids), "items": results},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"結果保存: {out}")


if __name__ == "__main__":
    main()
