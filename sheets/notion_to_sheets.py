"""
Notion → Google Sheets 自動同期スクリプト

NotionのエンジニアDBと案件DBをGoogle スプレッドシートに自動同期する
営業管理用の一覧表として活用可能

初回実行（認証セットアップ）:
  python notion_to_sheets.py --setup

同期実行:
  python notion_to_sheets.py

新規スプレッドシート作成（初回のみ）:
  python notion_to_sheets.py --create
"""

import os
import argparse
from datetime import datetime

import requests
from dotenv import dotenv_values
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ===== 設定 =====
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
]

BASE_DIR = os.path.dirname(__file__)
TOKEN_PATH = os.path.join(BASE_DIR, 'token_sheets.json')
CREDENTIALS_PATH = os.path.join(BASE_DIR, '..', 'gmail', 'credentials.json')
SPREADSHEET_ID_FILE = os.path.join(BASE_DIR, 'spreadsheet_id.txt')

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


# ===== Google Sheets 認証 =====

def get_sheets_service():
    """Google Sheets APIサービスを取得"""
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"credentials.jsonが見つかりません: {CREDENTIALS_PATH}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
        print(f"トークン保存: {TOKEN_PATH}")

    sheets = build('sheets', 'v4', credentials=creds)
    drive = build('drive', 'v3', credentials=creds)
    return sheets, drive


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
    items = props.get(key, {}).get("title", [])
    return "".join(t.get("plain_text", "") for t in items)


def extract_rich_text(props: dict, key: str) -> str:
    items = props.get(key, {}).get("rich_text", [])
    return "".join(t.get("plain_text", "") for t in items)


def extract_date(props: dict, key: str) -> str:
    d = props.get(key, {}).get("date")
    return d.get("start", "") if d else ""


def extract_select(props: dict, key: str) -> str:
    s = props.get(key, {}).get("select")
    return s.get("name", "") if s else ""


def extract_number(props: dict, key: str) -> str:
    n = props.get(key, {}).get("number")
    return str(n) if n is not None else ""


def extract_multi_select(props: dict, key: str) -> str:
    items = props.get(key, {}).get("multi_select", [])
    return ", ".join(i.get("name", "") for i in items)


def extract_phone(props: dict, key: str) -> str:
    return props.get(key, {}).get("phone_number", "") or ""


def extract_email(props: dict, key: str) -> str:
    return props.get(key, {}).get("email", "") or ""


# ===== Notionデータ → 行データ変換 =====

ENGINEER_HEADERS = [
    "名前", "稼働状況", "スキル", "単価（万円）",
    "稼働可能日", "経験年数", "連絡先", "メール",
    "備考", "最終更新日", "NotionページID"
]

PROJECT_HEADERS = [
    "案件名", "ステータス", "必須スキル", "予算（万円）",
    "開始日", "終了日", "クライアント", "備考",
    "最終更新日", "NotionページID"
]


def engineer_to_row(page: dict) -> list:
    """エンジニアページ → スプレッドシート行"""
    props = page.get('properties', {})
    last_edited = page.get('last_edited_time', '')[:10]
    note = extract_rich_text(props, '備考（LINEメモ）')[:200]  # 長すぎる場合は切り捨て

    return [
        extract_title(props, '名前'),
        extract_select(props, '稼働状況'),
        extract_multi_select(props, 'スキル'),
        extract_number(props, '単価（万円）'),
        extract_date(props, '稼働可能日'),
        extract_number(props, '経験年数'),
        extract_phone(props, '連絡先'),
        extract_email(props, 'メール'),
        note,
        last_edited,
        page['id'],
    ]


def project_to_row(page: dict) -> list:
    """案件ページ → スプレッドシート行"""
    props = page.get('properties', {})
    last_edited = page.get('last_edited_time', '')[:10]

    # 案件DBのプロパティ名が複数パターンに対応
    name = (extract_title(props, '案件名')
            or extract_title(props, 'タイトル')
            or extract_title(props, '名前'))
    status = (extract_select(props, 'ステータス')
              or extract_select(props, '状態'))
    skills = (extract_multi_select(props, '必須スキル')
              or extract_multi_select(props, 'スキル'))
    budget = (extract_number(props, '予算（万円）')
              or extract_number(props, '単価（万円）'))
    start = (extract_date(props, '開始日')
             or extract_date(props, '稼働開始日'))
    end = extract_date(props, '終了日') or extract_date(props, '稼働終了日')
    client = (extract_rich_text(props, 'クライアント')
              or extract_rich_text(props, '会社名')
              or extract_select(props, 'クライアント'))
    note = extract_rich_text(props, '備考')[:200]

    return [
        name, status, skills, budget,
        start, end, client, note,
        last_edited, page['id'],
    ]


# ===== スプレッドシート操作 =====

def create_spreadsheet(sheets_service, drive_service) -> str:
    """新規スプレッドシートを作成してIDを返す"""
    body = {
        'properties': {'title': 'SES営業管理シート'},
        'sheets': [
            {'properties': {'title': 'エンジニア一覧', 'index': 0}},
            {'properties': {'title': '案件一覧', 'index': 1}},
        ]
    }
    result = sheets_service.spreadsheets().create(body=body).execute()
    spreadsheet_id = result['spreadsheetId']
    spreadsheet_url = result['spreadsheetUrl']

    print(f"✅ スプレッドシート作成完了!")
    print(f"   URL: {spreadsheet_url}")
    print(f"   ID: {spreadsheet_id}")

    # IDをファイルに保存
    with open(SPREADSHEET_ID_FILE, 'w') as f:
        f.write(spreadsheet_id)
    print(f"   IDを保存: {SPREADSHEET_ID_FILE}")

    return spreadsheet_id


def get_spreadsheet_id() -> str:
    """保存済みスプレッドシートIDを取得"""
    if os.path.exists(SPREADSHEET_ID_FILE):
        with open(SPREADSHEET_ID_FILE) as f:
            return f.read().strip()
    raise FileNotFoundError(
        "スプレッドシートIDが見つかりません。\n"
        "先に: python notion_to_sheets.py --create を実行してください。"
    )


def write_sheet(sheets_service, spreadsheet_id: str, sheet_name: str, headers: list, rows: list):
    """シートにヘッダーと行データを書き込む（全上書き）"""
    all_data = [headers] + rows

    # シートをクリア
    sheets_service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1:Z10000"
    ).execute()

    # データを書き込む
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption='RAW',
        body={'values': all_data}
    ).execute()

    # ヘッダー行を太字・背景色で装飾
    sheet_id = get_sheet_id(sheets_service, spreadsheet_id, sheet_name)
    format_header(sheets_service, spreadsheet_id, sheet_id, len(headers))

    print(f"  ✅ {sheet_name}: {len(rows)}行を書き込みました")


def get_sheet_id(sheets_service, spreadsheet_id: str, sheet_name: str) -> int:
    """シート名からシートIDを取得"""
    info = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in info.get('sheets', []):
        if sheet['properties']['title'] == sheet_name:
            return sheet['properties']['sheetId']
    return 0


def format_header(sheets_service, spreadsheet_id: str, sheet_id: int, num_cols: int):
    """ヘッダー行を装飾（背景色 + 太字 + 列幅自動調整）"""
    requests_body = [
        {
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': num_cols,
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.2, 'green': 0.5, 'blue': 0.8},
                        'textFormat': {
                            'foregroundColor': {'red': 1, 'green': 1, 'blue': 1},
                            'bold': True,
                        },
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)',
            }
        },
        {
            'autoResizeDimensions': {
                'dimensions': {
                    'sheetId': sheet_id,
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': num_cols,
                }
            }
        }
    ]
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': requests_body}
    ).execute()


# ===== メイン処理 =====

def sync(spreadsheet_id: str, sheets_service):
    """Notion → Sheets 同期実行"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 同期開始")
    print(f"スプレッドシートID: {spreadsheet_id}")

    # エンジニア一覧
    print("\n--- エンジニア一覧 ---")
    engineer_pages = get_notion_db(NOTION_ENGINEER_DB_ID)
    print(f"取得: {len(engineer_pages)}件")
    engineer_rows = [engineer_to_row(p) for p in engineer_pages]
    write_sheet(sheets_service, spreadsheet_id, 'エンジニア一覧', ENGINEER_HEADERS, engineer_rows)

    # 案件一覧
    print("\n--- 案件一覧 ---")
    if NOTION_PROJECT_DB_ID:
        project_pages = get_notion_db(NOTION_PROJECT_DB_ID)
        print(f"取得: {len(project_pages)}件")
        if project_pages:
            project_rows = [project_to_row(p) for p in project_pages]
            write_sheet(sheets_service, spreadsheet_id, '案件一覧', PROJECT_HEADERS, project_rows)
        else:
            print("  案件DBにデータがありません（Notionで案件を登録してください）")
    else:
        print("  NOTION_PROJECT_DB_ID 未設定のためスキップ")

    print(f"\n✅ 同期完了")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Notion → Google Sheets 同期')
    parser.add_argument('--setup', action='store_true', help='初回OAuth認証セットアップ')
    parser.add_argument('--create', action='store_true', help='新規スプレッドシートを作成')
    args = parser.parse_args()

    sheets_service, drive_service = get_sheets_service()

    if args.setup:
        print("Google Sheets OAuth2 認証セットアップ完了！")
        print(f"トークン保存済み: {TOKEN_PATH}")

    elif args.create:
        spreadsheet_id = create_spreadsheet(sheets_service, drive_service)
        sync(spreadsheet_id, sheets_service)

    else:
        spreadsheet_id = get_spreadsheet_id()
        sync(spreadsheet_id, sheets_service)
