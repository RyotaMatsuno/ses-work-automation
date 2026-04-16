"""
Outlook（IMAP）→ Notion エンジニアDB 自動登録スクリプト

会社のOutlookメールを読み取り、パートナー企業からの
要員提案メールをNotionに自動登録する。

IMAP接続のみ使用（API登録不要・会社側にバレない）

実行方法:
  python outlook_to_notion.py

.envに設定が必要:
  OUTLOOK_EMAIL=your@company.co.jp
  OUTLOOK_PASSWORD=yourpassword
  OUTLOOK_IMAP_SERVER=outlook.office365.com  # Microsoft365の場合
  OUTLOOK_IMAP_PORT=993
"""

import imaplib
import email
from email.header import decode_header
import re
import os
import requests
from datetime import datetime
from dotenv import dotenv_values

# .envロード
env_path = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
if os.path.exists(env_path):
    config = dotenv_values(env_path)
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value

OUTLOOK_EMAIL     = os.environ['OUTLOOK_EMAIL']
OUTLOOK_PASSWORD  = os.environ['OUTLOOK_PASSWORD']
IMAP_SERVER       = os.environ.get('OUTLOOK_IMAP_SERVER', 'outlook.office365.com')
IMAP_PORT         = int(os.environ.get('OUTLOOK_IMAP_PORT', '993'))

NOTION_API_KEY        = os.environ['NOTION_API_KEY']
NOTION_ENGINEER_DB_ID = os.environ['NOTION_ENGINEER_DB_ID']

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# 処理済みメールを記録するファイル
PROCESSED_IDS_FILE = os.path.join(os.path.dirname(__file__), 'processed_ids.txt')

# 検索対象の件名キーワード（含む場合に処理）
SUBJECT_KEYWORDS = ['要員', 'エンジニア', 'スキル', '単価', '稼働', '提案', 'ご紹介']


# ===== IMAP接続 =====

def connect_imap():
    """IMAPサーバーに接続してログイン"""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(OUTLOOK_EMAIL, OUTLOOK_PASSWORD)
    return mail


# ===== 処理済みID管理 =====

def load_processed_ids():
    if not os.path.exists(PROCESSED_IDS_FILE):
        return set()
    with open(PROCESSED_IDS_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_processed_id(msg_id: str):
    with open(PROCESSED_IDS_FILE, 'a') as f:
        f.write(msg_id + '\n')


# ===== メール解析 =====

def decode_str(s):
    """メールヘッダーの文字列をデコード"""
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
    """メール本文（テキスト）を取得"""
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get('Content-Disposition', ''))
            if ct == 'text/plain' and 'attachment' not in cd:
                charset = part.get_content_charset() or 'utf-8'
                body = part.get_payload(decode=True).decode(charset, errors='ignore')
                break
    else:
        charset = msg.get_content_charset() or 'utf-8'
        body = msg.get_payload(decode=True).decode(charset, errors='ignore')
    return body

def should_process(subject: str) -> bool:
    """件名にキーワードが含まれるか判定"""
    return any(kw in subject for kw in SUBJECT_KEYWORDS)


# ===== エンジニア情報抽出 =====

def parse_engineer_info(text: str) -> dict:
    info = {}

    name_match = re.search(r'名前[：:]\s*(.+)', text)
    if name_match:
        info['name'] = name_match.group(1).strip()

    skill_match = re.search(r'スキル[：:]\s*(.+)', text)
    if skill_match:
        skills_raw = skill_match.group(1).strip()
        info['skills'] = [s.strip() for s in re.split(r'[,、，]', skills_raw)]

    price_match = re.search(r'単価[：:]\s*(\d+)', text)
    if price_match:
        info['price'] = int(price_match.group(1))

    date_match = re.search(r'稼働可能日[：:]\s*(\d{4}[年/\-]\d{1,2}[月/\-]\d{1,2})', text)
    if date_match:
        date_str = date_match.group(1)
        date_str = re.sub(
            r'(\d{4})年(\d{1,2})月(\d{1,2})日?',
            lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}",
            date_str
        )
        info['available_date'] = date_str

    exp_match = re.search(r'経験年数[：:]\s*(\d+)', text)
    if exp_match:
        info['experience'] = int(exp_match.group(1))

    tel_match = re.search(r'連絡先[：:]\s*([\d\-]+)', text)
    if tel_match:
        info['tel'] = tel_match.group(1).strip()

    email_match = re.search(r'メール[：:]\s*(\S+@\S+)', text)
    if email_match:
        info['email'] = email_match.group(1).strip()

    note_match = re.search(r'備考[：:]\s*(.+)', text)
    if note_match:
        info['note'] = note_match.group(1).strip()

    return info


# ===== Notion登録 =====

def register_to_notion(engineer_info: dict, raw_text: str, subject: str, sender: str) -> bool:
    if 'name' not in engineer_info:
        engineer_info['name'] = '（名前未記載）'

    valid_skills = ["Java", "Python", "PHP", "JavaScript", "TypeScript",
                    "C#", "Node.js", "React", "AWS", "インフラ"]

    source_info = f"【Outlookから自動登録】\n件名: {subject}\n送信者: {sender}\n\n"
    note_text = engineer_info.get('note', raw_text[:1500])
    full_note = (source_info + note_text)[:2000]

    properties = {
        "名前": {
            "title": [{"text": {"content": engineer_info.get('name', '未記載')}}]
        },
        "稼働状況": {
            "select": {"name": "稼働可能"}
        },
        "備考（LINEメモ）": {
            "rich_text": [{"text": {"content": full_note}}]
        }
    }

    if 'skills' in engineer_info:
        matched = [s for s in engineer_info['skills'] if s in valid_skills]
        if matched:
            properties["スキル"] = {"multi_select": [{"name": s} for s in matched]}

    if 'price' in engineer_info:
        properties["単価（万円）"] = {"number": engineer_info['price']}

    if 'available_date' in engineer_info:
        properties["稼働可能日"] = {"date": {"start": engineer_info['available_date']}}

    if 'experience' in engineer_info:
        properties["経験年数"] = {"number": engineer_info['experience']}

    if 'tel' in engineer_info:
        properties["連絡先"] = {"phone_number": engineer_info['tel']}

    if 'email' in engineer_info:
        properties["メール"] = {"email": engineer_info['email']}

    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": NOTION_ENGINEER_DB_ID}, "properties": properties}
    )

    if res.status_code == 200:
        print(f"  ✅ Notion登録成功: {engineer_info.get('name')}")
        return True
    else:
        print(f"  ❌ Notion登録エラー: {res.status_code} {res.text}")
        return False


# ===== メイン処理 =====

def run():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Outlook チェック開始")

    processed_ids = load_processed_ids()

    try:
        mail = connect_imap()
    except Exception as e:
        print(f"❌ IMAP接続失敗: {e}")
        print("  → OUTLOOK_EMAIL, OUTLOOK_PASSWORD, OUTLOOK_IMAP_SERVER を確認してください")
        return

    mail.select('INBOX')

    # 未読メールを検索
    _, msg_nums = mail.search(None, 'UNSEEN')
    all_ids = msg_nums[0].split()
    print(f"未読メール: {len(all_ids)}件")

    registered = 0
    skipped = 0

    for num in all_ids:
        _, data = mail.fetch(num, '(RFC822 BODY[HEADER.FIELDS (MESSAGE-ID)])')
        raw_header = data[1][1] if len(data) > 1 and data[1] else b''
        msg_id = email.message_from_bytes(raw_header).get('Message-ID', str(num))

        if msg_id in processed_ids:
            continue

        _, data = mail.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])

        subject = decode_str(msg.get('Subject', ''))
        sender  = decode_str(msg.get('From', ''))
        body    = get_email_body(msg)

        print(f"\n処理中: {subject[:50]} / {sender[:30]}")

        if not should_process(subject):
            print("  スキップ（キーワードなし）")
            save_processed_id(msg_id)
            skipped += 1
            continue

        engineer_info = parse_engineer_info(body)
        success = register_to_notion(engineer_info, body, subject, sender)

        save_processed_id(msg_id)

        if success:
            registered += 1
        else:
            skipped += 1

    mail.logout()
    print(f"\n完了: 登録 {registered}件 / スキップ {skipped}件")


if __name__ == '__main__':
    run()
