"""
Outlook（IMAP）→ Notion 自動登録スクリプト v2
- Claude AIでメール内容を解析（人材 or 案件を自動判定）
- 人材情報 → エンジニアDB登録
- 案件情報 → 案件DB登録
- 自由なフォーマットのメールも解析可能

実行方法:
  python outlook_to_notion.py
タスクスケジューラで毎日9時/13時/18時に自動実行
"""

import imaplib
import email
import json
import os
import re
import requests
from datetime import date
from email.header import decode_header
from dotenv import dotenv_values

env_path = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
if os.path.exists(env_path):
    config = dotenv_values(env_path)
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value

OUTLOOK_EMAIL     = os.environ.get('OUTLOOK_EMAIL', '')
OUTLOOK_PASSWORD  = os.environ.get('OUTLOOK_PASSWORD', '')
IMAP_SERVER       = os.environ.get('OUTLOOK_IMAP_SERVER', 'outlook.office365.com')
IMAP_PORT         = int(os.environ.get('OUTLOOK_IMAP_PORT', '993'))
NOTION_API_KEY    = os.environ.get('NOTION_API_KEY', '')
NOTION_ENGINEER_DB_ID = os.environ.get('NOTION_ENGINEER_DB_ID', '')
NOTION_PROJECT_DB_ID  = os.environ.get('NOTION_PROJECT_DB_ID', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

PROCESSED_IDS_FILE = os.path.join(os.path.dirname(__file__), 'processed_ids.txt')

# 処理対象キーワード（件名に含まれる場合のみ処理）
SUBJECT_KEYWORDS = [
    '要員', 'エンジニア', 'スキル', '単価', '稼働', '提案', 'ご紹介',
    '案件', '募集', '参画', '開発', 'PG', 'SE', 'インフラ', 'Java',
    'Python', 'PHP', 'AWS', 'クラウド', 'システム'
]


# ============================================================
# Claude AI呼び出し
# ============================================================

def call_claude(system_prompt: str, user_message: str) -> str:
    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}]
        },
        timeout=30
    )
    if res.status_code == 200:
        return res.json()["content"][0]["text"]
    print(f"Claude APIエラー: {res.status_code} {res.text}")
    return ""


def ai_classify_email(subject: str, body: str) -> dict:
    """メールの件名と本文からAIが人材/案件を判定し構造化データを返す"""
    system = """あなたはSES（システムエンジニアリングサービス）業界の情報解析AIです。
メールの件名と本文を解析して、以下のJSON形式のみで返答してください。マークダウンや説明文は不要です。

【人材情報と判断する基準】
- エンジニアの名前、スキル、単価、稼働可能日などが含まれる
- 「ご紹介」「要員」「スキルシート」などの言葉がある

【案件情報と判断する基準】
- 案件名、必須スキル、勤務地、期間などが含まれる
- 「募集」「案件」「参画」「ご提案」などの言葉がある

人材情報の場合:
{
  "type": "engineer",
  "name": "氏名（不明なら空文字）",
  "skills": ["スキル1", "スキル2"],
  "price": 単価の数値（万円、不明なら0）,
  "available_date": "YYYY-MM-DD形式（不明なら空文字）",
  "experience_years": 経験年数の数値（不明なら0）,
  "company": "所属会社名（不明なら空文字）",
  "note": "備考・その他情報"
}

案件情報の場合:
{
  "type": "project",
  "name": "案件名（不明なら空文字）",
  "required_skills": ["必須スキル1", "必須スキル2"],
  "optional_skills": ["尚可スキル1"],
  "price": 案件単価の数値（万円、不明なら0）,
  "start_date": "YYYY-MM-DD形式（不明なら空文字）",
  "location": "勤務地（不明なら空文字）",
  "remote": "可" または "不可" または "一部可" または "不明",
  "period": "期間",
  "interview_count": 面談回数の数値（不明なら1）,
  "foreign_ok": false,
  "note": "業務内容・その他情報"
}

どちらでもない場合:
{
  "type": "other",
  "note": "内容の要約"
}"""

    content = f"件名: {subject}\n\n本文:\n{body[:3000]}"
    result = call_claude(system, content)
    try:
        clean = re.sub(r'```json|```', '', result).strip()
        return json.loads(clean)
    except Exception as e:
        print(f"  JSON解析エラー: {e}")
        return {"type": "other", "note": f"{subject}\n{body[:500]}"}


# ============================================================
# Notion登録
# ============================================================

VALID_SKILLS = [
    "Java", "Python", "PHP", "JavaScript", "TypeScript", "C#", "Node.js",
    "React", "AWS", "インフラ", "Go", "Ruby", "Swift", "Kotlin", "Vue.js",
    "Angular", "Docker", "Kubernetes", "GCP", "Azure", "Spring",
    "MySQL", "PostgreSQL", "Oracle", "MongoDB", "Linux"
]


def register_engineer(info: dict, subject: str, sender: str) -> bool:
    name = info.get("name") or "（名前未記載）"
    note = f"【Outlookから自動登録】\n件名: {subject}\n送信者: {sender}\n\n{info.get('note', '')}"

    properties = {
        "名前": {"title": [{"text": {"content": name}}]},
        "稼働状況": {"select": {"name": "稼働可能"}},
        "備考（LINEメモ）": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }

    skills = [s for s in info.get("skills", []) if s in VALID_SKILLS]
    if skills:
        properties["スキル"] = {"multi_select": [{"name": s} for s in skills]}
    if info.get("price"):
        properties["単価（万円）"] = {"number": info["price"]}
    if info.get("available_date"):
        properties["稼働可能日"] = {"date": {"start": info["available_date"]}}
    if info.get("experience_years"):
        properties["経験年数"] = {"number": info["experience_years"]}

    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": NOTION_ENGINEER_DB_ID}, "properties": properties}
    )
    if res.status_code == 200:
        print(f"  ✅ エンジニア登録: {name}")
        return True
    print(f"  ❌ エンジニア登録エラー: {res.status_code} {res.text}")
    return False


def register_project(info: dict, subject: str, sender: str) -> bool:
    name = info.get("name") or f"（案件: {subject[:30]}）"
    note = f"【Outlookから自動登録】\n件名: {subject}\n送信者: {sender}\n\n{info.get('note', '')}"

    properties = {
        "案件名": {"title": [{"text": {"content": name}}]},
        "ステータス": {"select": {"name": "募集中"}},
        "備考": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }

    req_skills = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt_skills = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req_skills:
        properties["必要スキル"] = {"multi_select": [{"name": s} for s in req_skills]}
    if opt_skills:
        properties["尚可スキル"] = {"multi_select": [{"name": s} for s in opt_skills]}
    if info.get("price"):
        properties["単価（万円）"] = {"number": info["price"]}
    if info.get("start_date"):
        properties["開始日"] = {"date": {"start": info["start_date"]}}
    if info.get("location"):
        properties["勤務地"] = {"rich_text": [{"text": {"content": info["location"]}}]}

    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": NOTION_PROJECT_DB_ID}, "properties": properties}
    )
    if res.status_code == 200:
        print(f"  ✅ 案件登録: {name}")
        return True
    print(f"  ❌ 案件登録エラー: {res.status_code} {res.text}")
    return False


# ============================================================
# メール処理
# ============================================================

def decode_str(s):
    if s is None:
        return ''
    parts = decode_header(s)
    result = ''
    for part, enc in parts:
        if isinstance(part, bytes):
            result += part.decode(enc or 'utf-8', errors='ignore')
        else:
            result += str(part)
    return result


def get_email_body(msg) -> str:
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain' and 'attachment' not in str(part.get('Content-Disposition', '')):
                charset = part.get_content_charset() or 'utf-8'
                body = part.get_payload(decode=True).decode(charset, errors='ignore')
                break
    else:
        charset = msg.get_content_charset() or 'utf-8'
        body = msg.get_payload(decode=True).decode(charset, errors='ignore')
    return body


def load_processed_ids() -> set:
    if not os.path.exists(PROCESSED_IDS_FILE):
        return set()
    with open(PROCESSED_IDS_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())


def save_processed_id(msg_id: str):
    with open(PROCESSED_IDS_FILE, 'a') as f:
        f.write(msg_id + '\n')


def should_process(subject: str) -> bool:
    return any(kw in subject for kw in SUBJECT_KEYWORDS)


# ============================================================
# メイン処理
# ============================================================

def run():
    from datetime import datetime
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Outlook チェック開始")

    processed_ids = load_processed_ids()

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(OUTLOOK_EMAIL, OUTLOOK_PASSWORD)
    except Exception as e:
        print(f"❌ IMAP接続失敗: {e}")
        return

    mail.select('INBOX')
    _, msg_nums = mail.search(None, 'UNSEEN')
    all_ids = msg_nums[0].split()
    print(f"未読メール: {len(all_ids)}件")

    registered_eng = registered_proj = skipped = 0

    for num in all_ids:
        _, data = mail.fetch(num, '(BODY[HEADER.FIELDS (MESSAGE-ID)])')
        raw_header = data[1][1] if len(data) > 1 and data[1] else b''
        msg_id = email.message_from_bytes(raw_header).get('Message-ID', str(num))

        if msg_id in processed_ids:
            continue

        _, data = mail.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])
        subject = decode_str(msg.get('Subject', ''))
        sender  = decode_str(msg.get('From', ''))
        body    = get_email_body(msg)

        print(f"\n処理中: {subject[:50]}")

        if not should_process(subject):
            print("  スキップ（対象キーワードなし）")
            save_processed_id(msg_id)
            skipped += 1
            continue

        # AI判定・登録
        info = ai_classify_email(subject, body)
        msg_type = info.get("type", "other")
        print(f"  AI判定: {msg_type}")

        if msg_type == "engineer":
            if register_engineer(info, subject, sender):
                registered_eng += 1
            else:
                skipped += 1
        elif msg_type == "project":
            if register_project(info, subject, sender):
                registered_proj += 1
            else:
                skipped += 1
        else:
            print("  スキップ（人材・案件情報なし）")
            skipped += 1

        save_processed_id(msg_id)

    mail.logout()
    print(f"\n完了: エンジニア登録 {registered_eng}件 / 案件登録 {registered_proj}件 / スキップ {skipped}件")


if __name__ == '__main__':
    run()
