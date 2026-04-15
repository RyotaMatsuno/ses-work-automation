"""
Gmail → Notion エンジニアDB 自動登録スクリプト

パートナー企業からのメール（要員提案）を自動的に読み取り
NotionのエンジニアDBに登録する

初回実行:
  python gmail_to_notion.py --setup
  （ブラウザでGoogleアカウント認証が開きます）

定期実行（自動チェック）:
  python gmail_to_notion.py
"""

import os
import re
import json
import base64
import argparse
from datetime import datetime, timedelta
from email import message_from_bytes
from email.header import decode_header

import requests
from dotenv import dotenv_values
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ===== 設定 =====
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
TOKEN_PATH = os.path.join(os.path.dirname(__file__), 'token.json')
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), 'credentials.json')
PROCESSED_LABEL = 'Notion登録済み'

# 検索クエリ（未読 かつ ラベルなし のメール。必要に応じてカスタマイズ）
# 例: 'from:partner.com is:unread' で特定ドメインのみ対象
GMAIL_SEARCH_QUERY = 'is:unread -label:Notion登録済み subject:(要員 OR エンジニア OR スキル OR 単価 OR 稼働)'

# .envロード
env_path = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
if os.path.exists(env_path):
    config = dotenv_values(env_path)
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value

NOTION_API_KEY = os.environ['NOTION_API_KEY']
NOTION_ENGINEER_DB_ID = os.environ['NOTION_ENGINEER_DB_ID']

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


# ===== Gmail認証 =====

def get_gmail_service():
    """Gmail APIサービスを取得（OAuth2認証）"""
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"credentials.jsonが見つかりません: {CREDENTIALS_PATH}\n"
                    "Google Cloud ConsoleでOAuth2クライアントIDをダウンロードし、"
                    f"{CREDENTIALS_PATH} に配置してください。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


# ===== メール解析 =====

def get_email_body(msg_data: dict) -> str:
    """メールのテキスト本文を取得"""
    payload = msg_data.get('payload', {})

    def extract_text(part):
        mime = part.get('mimeType', '')
        body = part.get('body', {})
        data = body.get('data', '')

        if mime == 'text/plain' and data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        parts = part.get('parts', [])
        for p in parts:
            result = extract_text(p)
            if result:
                return result
        return ''

    return extract_text(payload)


def get_email_subject(msg_data: dict) -> str:
    """件名を取得"""
    headers = msg_data.get('payload', {}).get('headers', [])
    for h in headers:
        if h['name'].lower() == 'subject':
            raw = h['value']
            decoded_parts = decode_header(raw)
            subject = ''
            for part, enc in decoded_parts:
                if isinstance(part, bytes):
                    subject += part.decode(enc or 'utf-8', errors='ignore')
                else:
                    subject += part
            return subject
    return '（件名なし）'


def get_email_from(msg_data: dict) -> str:
    """送信者を取得"""
    headers = msg_data.get('payload', {}).get('headers', [])
    for h in headers:
        if h['name'].lower() == 'from':
            return h['value']
    return ''


def parse_engineer_info(text: str) -> dict:
    """
    メール本文からエンジニア情報を抽出

    対応フォーマット（LINE webhookと共通）:
    名前：山田太郎
    スキル：Java, Python, AWS
    単価：70万円
    稼働可能日：2024年4月1日
    経験年数：5年
    連絡先：090-1234-5678
    メール：yamada@example.com
    備考：フルリモート希望
    """
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
    """NotionのエンジニアDBにエンジニア情報を登録"""

    if 'name' not in engineer_info:
        engineer_info['name'] = '（名前未記載）'

    valid_skills = ["Java", "Python", "PHP", "JavaScript", "TypeScript",
                    "C#", "Node.js", "React", "AWS", "インフラ"]

    # 備考にメール件名・送信者も含める
    note_text = engineer_info.get('note', '')
    source_info = f"【Gmailから自動登録】\n件名: {subject}\n送信者: {sender}\n\n"
    if not note_text:
        note_text = raw_text[:1500]
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
        matched_skills = [s for s in engineer_info['skills'] if s in valid_skills]
        if matched_skills:
            properties["スキル"] = {
                "multi_select": [{"name": s} for s in matched_skills]
            }

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

    data = {
        "parent": {"database_id": NOTION_ENGINEER_DB_ID},
        "properties": properties
    }

    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=data
    )

    if res.status_code == 200:
        print(f"  ✅ Notion登録成功: {engineer_info.get('name')}")
        return True
    else:
        print(f"  ❌ Notion登録エラー: {res.status_code} {res.text}")
        return False


# ===== Gmailラベル管理 =====

def get_or_create_label(service, label_name: str) -> str:
    """ラベルIDを取得（なければ作成）"""
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    for label in labels:
        if label['name'] == label_name:
            return label['id']

    # 作成
    new_label = service.users().labels().create(
        userId='me',
        body={'name': label_name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
    ).execute()
    print(f"ラベル作成: {label_name}")
    return new_label['id']


def apply_label_and_mark_read(service, msg_id: str, label_id: str):
    """メールにラベルを付けて既読にする"""
    service.users().messages().modify(
        userId='me',
        id=msg_id,
        body={
            'addLabelIds': [label_id],
            'removeLabelIds': ['UNREAD']
        }
    ).execute()


# ===== メイン処理 =====

def run():
    """未読メールをスキャンしてNotionに登録"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Gmail チェック開始")

    service = get_gmail_service()
    label_id = get_or_create_label(service, PROCESSED_LABEL)

    # 対象メールを検索
    results = service.users().messages().list(
        userId='me',
        q=GMAIL_SEARCH_QUERY,
        maxResults=50
    ).execute()

    messages = results.get('messages', [])
    print(f"対象メール: {len(messages)}件")

    registered = 0
    skipped = 0

    for msg_ref in messages:
        msg_id = msg_ref['id']
        msg_data = service.users().messages().get(
            userId='me', id=msg_id, format='full'
        ).execute()

        subject = get_email_subject(msg_data)
        sender = get_email_from(msg_data)
        body = get_email_body(msg_data)

        print(f"\n処理中: {subject[:50]} / {sender[:30]}")

        if not body.strip():
            print("  スキップ（本文なし）")
            apply_label_and_mark_read(service, msg_id, label_id)
            skipped += 1
            continue

        engineer_info = parse_engineer_info(body)
        success = register_to_notion(engineer_info, body, subject, sender)

        apply_label_and_mark_read(service, msg_id, label_id)

        if success:
            registered += 1
        else:
            skipped += 1

    print(f"\n完了: 登録 {registered}件 / スキップ {skipped}件")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gmail → Notion エンジニア自動登録')
    parser.add_argument('--setup', action='store_true', help='初回OAuth認証セットアップ')
    args = parser.parse_args()

    if args.setup:
        print("Google OAuth2 認証セットアップを開始します...")
        service = get_gmail_service()
        profile = service.users().getProfile(userId='me').execute()
        print(f"認証成功！ アカウント: {profile['emailAddress']}")
        print(f"トークン保存済み: {TOKEN_PATH}")
    else:
        run()
