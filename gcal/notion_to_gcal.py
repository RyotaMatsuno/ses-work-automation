"""
Notion → Google Calendar 自動連携スクリプト

NotionのエンジニアDBと案件DBから稼働日・開始日を読み取り
Google カレンダーに自動登録する

初回実行（認証セットアップ）:
  python notion_to_gcal.py --setup

定期実行:
  python notion_to_gcal.py
"""

import os
import argparse
from datetime import datetime, timedelta

import requests
from dotenv import dotenv_values
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ===== 設定 =====
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
]

BASE_DIR = os.path.dirname(__file__)
TOKEN_PATH = os.path.join(BASE_DIR, 'token_calendar.json')
CREDENTIALS_PATH = os.path.join(BASE_DIR, '..', 'gmail', 'credentials.json')

# カレンダーID（'primary' = メインカレンダー）
CALENDAR_ID = 'primary'

# イベントカラー（Google Calendar の colorId）
COLOR_ENGINEER = '2'   # セージ（緑）
COLOR_PROJECT = '9'    # ブルーベリー（青）
COLOR_MATCH = '11'     # トマト（赤）

# .envロード
env_path = os.path.join(BASE_DIR, '..', 'config', '.env')
if os.path.exists(env_path):
    config = dotenv_values(env_path)
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value

NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
NOTION_ENGINEER_DB_ID = os.environ.get('NOTION_ENGINEER_DB_ID', '')
NOTION_PROJECT_DB_ID = os.environ.get('NOTION_PROJECT_DB_ID', '')

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


# ===== Google Calendar 認証 =====

def get_calendar_service():
    """Google Calendar APIサービスを取得"""
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
                    "gmail/credentials.json を確認してください。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
        print(f"トークン保存: {TOKEN_PATH}")

    return build('calendar', 'v3', credentials=creds)


# ===== Notion データ取得 =====

def get_notion_db(database_id: str) -> list:
    """NotionDBの全ページを取得"""
    results = []
    payload = {"page_size": 100}
    while True:
        res = requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=NOTION_HEADERS,
            json=payload
        )
        data = res.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results


def extract_title(props: dict, key: str) -> str:
    """titleプロパティから文字列を取得"""
    items = props.get(key, {}).get("title", [])
    return "".join(t.get("plain_text", "") for t in items) or "（名前未記載）"


def extract_date(props: dict, key: str) -> str | None:
    """dateプロパティからYYYY-MM-DD文字列を取得"""
    d = props.get(key, {}).get("date")
    if d:
        return d.get("start")
    return None


def extract_select(props: dict, key: str) -> str:
    """selectプロパティから値を取得"""
    s = props.get(key, {}).get("select")
    return s.get("name", "") if s else ""


def extract_number(props: dict, key: str) -> int | None:
    """numberプロパティから値を取得"""
    return props.get(key, {}).get("number")


def extract_multi_select(props: dict, key: str) -> list[str]:
    """multi_selectプロパティからリストを取得"""
    items = props.get(key, {}).get("multi_select", [])
    return [i.get("name", "") for i in items]


# ===== 既存イベント管理 =====

def get_existing_event_ids(service) -> set:
    """既に登録済みのNotionページIDをカレンダーイベントの説明から収集"""
    existing = set()
    page_token = None
    now = datetime.utcnow()
    time_min = (now - timedelta(days=30)).isoformat() + 'Z'
    time_max = (now + timedelta(days=365)).isoformat() + 'Z'

    while True:
        result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            pageToken=page_token,
            singleEvents=True,
            maxResults=500
        ).execute()

        for event in result.get('items', []):
            desc = event.get('description', '')
            # "notion_page_id: XXXX" 形式でIDを埋め込む
            if 'notion_page_id:' in desc:
                for line in desc.split('\n'):
                    if line.startswith('notion_page_id:'):
                        page_id = line.split(':', 1)[1].strip()
                        existing.add(page_id)

        page_token = result.get('nextPageToken')
        if not page_token:
            break

    return existing


def create_event(service, summary: str, date_str: str, description: str, color_id: str):
    """終日イベントをGoogle Calendarに作成"""
    event = {
        'summary': summary,
        'description': description,
        'start': {'date': date_str},
        'end': {'date': date_str},
        'colorId': color_id,
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},  # 前日メール
                {'method': 'popup', 'minutes': 60},        # 1時間前ポップアップ
            ]
        }
    }
    service.events().insert(calendarId=CALENDAR_ID, body=event).execute()


# ===== メイン処理 =====

def sync_engineers(service, existing_ids: set) -> int:
    """エンジニアの稼働可能日をカレンダーに登録"""
    print("\n--- エンジニア稼働可能日の同期 ---")
    pages = get_notion_db(NOTION_ENGINEER_DB_ID)
    count = 0

    for page in pages:
        page_id = page['id']
        props = page.get('properties', {})

        name = extract_title(props, '名前')
        available_date = extract_date(props, '稼働可能日')
        status = extract_select(props, '稼働状況')
        skills = extract_multi_select(props, 'スキル')
        price = extract_number(props, '単価（万円）')

        if not available_date:
            continue
        if page_id in existing_ids:
            print(f"  スキップ（登録済み）: {name}")
            continue

        skill_str = ', '.join(skills) if skills else '未記載'
        price_str = f"{price}万円" if price else '未記載'
        description = (
            f"【エンジニア稼働可能日】\n"
            f"名前: {name}\n"
            f"稼働状況: {status}\n"
            f"スキル: {skill_str}\n"
            f"単価: {price_str}\n"
            f"notion_page_id: {page_id}"
        )

        summary = f"🟢 {name} 稼働開始可能"
        create_event(service, summary, available_date, description, COLOR_ENGINEER)
        print(f"  ✅ 登録: {summary} ({available_date})")
        count += 1

    return count


def sync_projects(service, existing_ids: set) -> int:
    """案件の開始日をカレンダーに登録"""
    print("\n--- 案件開始日の同期 ---")

    if not NOTION_PROJECT_DB_ID:
        print("  NOTION_PROJECT_DB_ID が未設定のためスキップ")
        return 0

    pages = get_notion_db(NOTION_PROJECT_DB_ID)

    if not pages:
        print("  案件DBにデータがありません（Notionで案件を登録してください）")
        return 0

    count = 0
    for page in pages:
        page_id = page['id']
        props = page.get('properties', {})

        # 案件DBのプロパティ名に合わせて調整
        name = extract_title(props, '案件名')
        start_date = extract_date(props, '開始日') or extract_date(props, '稼働開始日')
        required_skills = extract_multi_select(props, '必須スキル') or extract_multi_select(props, 'スキル')
        budget = extract_number(props, '予算（万円）') or extract_number(props, '単価（万円）')
        status = extract_select(props, 'ステータス') or extract_select(props, '状態')

        if not start_date:
            continue
        if page_id in existing_ids:
            print(f"  スキップ（登録済み）: {name}")
            continue

        skill_str = ', '.join(required_skills) if required_skills else '未記載'
        budget_str = f"{budget}万円" if budget else '未記載'
        description = (
            f"【案件開始日】\n"
            f"案件名: {name}\n"
            f"ステータス: {status}\n"
            f"必須スキル: {skill_str}\n"
            f"予算: {budget_str}\n"
            f"notion_page_id: {page_id}"
        )

        summary = f"🔵 {name} 開始"
        create_event(service, summary, start_date, description, COLOR_PROJECT)
        print(f"  ✅ 登録: {summary} ({start_date})")
        count += 1

    return count


def run():
    """Notion → Google Calendar 同期を実行"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Notion → Google Calendar 同期開始")

    service = get_calendar_service()

    print("既存イベントを確認中...")
    existing_ids = get_existing_event_ids(service)
    print(f"登録済みNotionページ: {len(existing_ids)}件")

    eng_count = sync_engineers(service, existing_ids)
    proj_count = sync_projects(service, existing_ids)

    print(f"\n✅ 完了: エンジニア {eng_count}件, 案件 {proj_count}件 をカレンダーに登録しました")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Notion → Google Calendar 同期')
    parser.add_argument('--setup', action='store_true', help='初回OAuth認証セットアップ')
    args = parser.parse_args()

    if args.setup:
        print("Google Calendar OAuth2 認証セットアップを開始します...")
        service = get_calendar_service()
        calendars = service.calendarList().list().execute()
        print("認証成功！ アクセス可能なカレンダー:")
        for cal in calendars.get('items', []):
            primary = " ← メイン" if cal.get('primary') else ""
            print(f"  {cal['summary']}{primary}")
        print(f"\nトークン保存済み: {TOKEN_PATH}")
    else:
        run()
