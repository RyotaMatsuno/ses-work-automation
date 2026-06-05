"""
Outlook（IMAP）→ Notion 自動登録スクリプト v3
- 複数メールアカウント対応
- Claude AIでメール内容を解析（人材 or 案件を自動判定）
- 人材情報 → エンジニアDB登録
- 案件情報 → 案件DB登録

実行方法:
  python outlook_to_notion.py
タスクスケジューラで毎日9時/13時/18時に自動実行

.envに設定が必要:
  # アカウント1（現在のTERRA用）
  OUTLOOK_EMAIL=sessales@terra-ltd.co.jp
  OUTLOOK_PASSWORD=xxxx
  OUTLOOK_IMAP_SERVER=mail65.onamae.ne.jp
  OUTLOOK_IMAP_PORT=993

  # アカウント2（個人アドレス用）
  OUTLOOK_EMAIL2=xxxx@xxxx.com
  OUTLOOK_PASSWORD2=xxxx
  OUTLOOK_IMAP_SERVER2=outlook.office365.com
  OUTLOOK_IMAP_PORT2=993

  # アカウント3（追加用・未使用ならそのままでOK）
  OUTLOOK_EMAIL3=
  OUTLOOK_PASSWORD3=
  OUTLOOK_IMAP_SERVER3=
  OUTLOOK_IMAP_PORT3=993
"""

import imaplib
import email
import json
import os
import re
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import requests
from datetime import datetime
from email.header import decode_header
from dotenv import dotenv_values

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.ledger import can_spend as ledger_can_spend, record as ledger_record
from common.model_config import TEXT_MODEL

env_path = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
if os.path.exists(env_path):
    config = dotenv_values(env_path)
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value

NOTION_API_KEY        = os.environ.get('NOTION_API_KEY', '')
NOTION_ENGINEER_DB_ID = os.environ.get('NOTION_ENGINEER_DB_ID', '')
NOTION_PROJECT_DB_ID  = os.environ.get('NOTION_PROJECT_DB_ID', '')
ANTHROPIC_API_KEY     = os.environ.get('ANTHROPIC_API_KEY', '')

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# 複数アカウント設定を自動収集
def get_accounts() -> list:
    """
    .envから複数アカウント設定を読み込む。
    OUTLOOK_EMAIL, OUTLOOK_EMAIL2, OUTLOOK_EMAIL3... に対応。
    """
    accounts = []
    suffixes = ['', '2', '3', '4', '5']
    for s in suffixes:
        email_addr = os.environ.get(f'OUTLOOK_EMAIL{s}', '')
        password   = os.environ.get(f'OUTLOOK_PASSWORD{s}', '')
        server     = os.environ.get(f'OUTLOOK_IMAP_SERVER{s}', 'outlook.office365.com')
        port       = int(os.environ.get(f'OUTLOOK_IMAP_PORT{s}', '993'))
        if email_addr and password:
            accounts.append({
                'email': email_addr,
                'password': password,
                'server': server,
                'port': port,
                'label': f'アカウント{s if s else "1"}({email_addr})'
            })
    return accounts

PROCESSED_IDS_FILE = os.path.join(os.path.dirname(__file__), 'processed_ids.txt')

SUBJECT_KEYWORDS = [
    '要員', 'エンジニア', 'スキル', '単価', '稼働', '提案', 'ご紹介',
    '案件', '募集', '参画', '開発', 'PG', 'SE', 'インフラ', 'Java',
    'Python', 'PHP', 'AWS', 'クラウド', 'システム'
]

VALID_SKILLS = [
    "Java", "Python", "PHP", "JavaScript", "TypeScript", "C#", "Node.js",
    "React", "AWS", "インフラ", "Go", "Ruby", "Swift", "Kotlin", "Vue.js",
    "Angular", "Docker", "Kubernetes", "GCP", "Azure", "Spring",
    "MySQL", "PostgreSQL", "Oracle", "MongoDB", "Linux"
]


# ============================================================
# Claude AI呼び出し
# ============================================================

def call_claude(system_prompt: str, user_message: str) -> str:
    model = TEXT_MODEL
    est_in = (len(system_prompt) + len(user_message)) // 4 + 200
    est_out = 1000
    if not ledger_can_spend(est_in, est_out, model):
        print(f"cost_guard: Outlook分類API停止 model={model}")
        return ""
    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": model,
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}]
        },
        timeout=30
    )
    if res.status_code == 200:
        data = res.json()
        usage = data.get("usage", {})
        ledger_record(
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
            data.get("model") or model,
            "outlook_to_notion",
        )
        return data["content"][0]["text"]
    print(f"Claude APIエラー: {res.status_code}")
    return ""


def ai_classify_email(subject: str, body: str) -> dict:
    system = """あなたはSES業界の情報解析AIです。
メールの件名と本文を解析して、JSON形式のみで返答してください。説明文は不要です。

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
  "required_skills": ["必須スキル1"],
  "optional_skills": ["尚可スキル1"],
  "price": 案件単価の数値（万円、不明なら0）,
  "start_date": "YYYY-MM-DD形式（不明なら空文字）",
  "location": "勤務地（不明なら空文字）",
  "remote": "可または不可または一部可または不明",
  "period": "期間",
  "interview_count": 面談回数の数値（不明なら1）,
  "foreign_ok": false,
  "note": "業務内容・その他情報"
}

どちらでもない場合:
{"type": "other", "note": "内容の要約"}"""

    result = call_claude(system, f"件名: {subject}\n\n本文:\n{body[:3000]}")
    try:
        clean = re.sub(r'```json|```', '', result).strip()
        return json.loads(clean)
    except:
        return {"type": "other", "note": f"{subject}"}


# ============================================================
# Notion登録
# ============================================================

def register_engineer(info: dict, subject: str, sender: str, account_label: str) -> bool:
    name = info.get("name") or "（名前未記載）"
    note = f"【Outlookから自動登録 - {account_label}】\n件名: {subject}\n送信者: {sender}\n\n{info.get('note', '')}"
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
    print(f"  ❌ エンジニア登録エラー: {res.status_code}")
    return False


def register_project(info: dict, subject: str, sender: str, account_label: str) -> bool:
    name = info.get("name") or f"（案件: {subject[:30]}）"
    note = f"【Outlookから自動登録 - {account_label}】\n件名: {subject}\n送信者: {sender}\n\n{info.get('note', '')}"
    properties = {
        "案件名": {"title": [{"text": {"content": name}}]},
        "ステータス": {"select": {"name": "募集中"}},
        "備考": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req:
        properties["必要スキル"] = {"multi_select": [{"name": s} for s in req]}
    if opt:
        properties["尚可スキル"] = {"multi_select": [{"name": s} for s in opt]}
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
    print(f"  ❌ 案件登録エラー: {res.status_code}")
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
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain' and 'attachment' not in str(part.get('Content-Disposition', '')):
                charset = part.get_content_charset() or 'utf-8'
                return part.get_payload(decode=True).decode(charset, errors='ignore')
    else:
        charset = msg.get_content_charset() or 'utf-8'
        return msg.get_payload(decode=True).decode(charset, errors='ignore')
    return ''


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


def process_account(account: dict, processed_ids: set) -> tuple[int, int, int]:
    """1アカウントの未読メールを処理。(eng登録数, proj登録数, スキップ数)を返す"""
    label = account['label']
    print(f"\n--- {label} ---")

    try:
        mail = imaplib.IMAP4_SSL(account['server'], account['port'])
        mail.login(account['email'], account['password'])
    except Exception as e:
        print(f"  ❌ 接続失敗: {e}")
        return 0, 0, 0

    mail.select('INBOX')
    _, msg_nums = mail.search(None, 'UNSEEN')
    all_ids = msg_nums[0].split()
    print(f"  未読: {len(all_ids)}件")

    eng = proj = skip = 0

    for num in all_ids:
        _, data = mail.fetch(num, '(BODY[HEADER.FIELDS (MESSAGE-ID)])')
        raw_header = data[1][1] if len(data) > 1 and data[1] else b''
        msg_id = email.message_from_bytes(raw_header).get('Message-ID', str(num))

        if msg_id in processed_ids:
            continue

        _, data = mail.fetch(num, '(RFC822)')
        msg     = email.message_from_bytes(data[0][1])
        subject = decode_str(msg.get('Subject', ''))
        sender  = decode_str(msg.get('From', ''))
        body    = get_email_body(msg)

        print(f"  処理中: {subject[:40]}")

        if not should_process(subject):
            print("    スキップ（キーワードなし）")
            save_processed_id(msg_id)
            skip += 1
            continue

        info = ai_classify_email(subject, body)
        t    = info.get("type", "other")
        print(f"    AI判定: {t}")

        if t == "engineer":
            if register_engineer(info, subject, sender, label):
                eng += 1
            else:
                skip += 1
        elif t == "project":
            if register_project(info, subject, sender, label):
                proj += 1
            else:
                skip += 1
        else:
            print("    スキップ（人材・案件情報なし）")
            skip += 1

        save_processed_id(msg_id)
        processed_ids.add(msg_id)

    mail.logout()
    return eng, proj, skip


# ============================================================
# メイン
# ============================================================

def run():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Outlook チェック開始（複数アカウント対応）")

    accounts = get_accounts()
    if not accounts:
        print("❌ メールアカウントが設定されていません。.envを確認してください。")
        return

    print(f"対象アカウント: {len(accounts)}件")
    for a in accounts:
        print(f"  - {a['label']}")

    processed_ids = load_processed_ids()

    total_eng = total_proj = total_skip = 0

    for account in accounts:
        eng, proj, skip = process_account(account, processed_ids)
        total_eng  += eng
        total_proj += proj
        total_skip += skip

    print(f"\n{'='*40}")
    print(f"完了: エンジニア登録 {total_eng}件 / 案件登録 {total_proj}件 / スキップ {total_skip}件")


if __name__ == '__main__':
    run()
