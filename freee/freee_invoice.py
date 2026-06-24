"""
Freee 請求書自動生成スクリプト
NotionのエンジニアDB（稼働中）から稼働者情報を取得し、
Freee APIで請求書を自動生成する。

実行タイミング: 毎月25日（翌月請求分）
手動実行: python freee_invoice.py

.envに追加が必要:
  FREEE_ACCESS_TOKEN=your_access_token
  FREEE_COMPANY_ID=your_company_id（事業所ID）

Freee APIドキュメント:
  https://developer.freee.co.jp/reference/accounting/reference
"""

import os
from datetime import date

import requests
from dateutil.relativedelta import relativedelta
from dotenv import dotenv_values

# .envロード
env_path = os.path.join(os.path.dirname(__file__), "..", "config", ".env")
if os.path.exists(env_path):
    config = dotenv_values(env_path)
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_ENGINEER_DB_ID = os.environ.get("NOTION_ENGINEER_DB_ID", "")
FREEE_ACCESS_TOKEN = os.environ.get("FREEE_ACCESS_TOKEN", "")
FREEE_COMPANY_ID = os.environ.get("FREEE_COMPANY_ID", "")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

FREEE_HEADERS = {"Authorization": f"Bearer {FREEE_ACCESS_TOKEN}", "Content-Type": "application/json"}

FREEE_BASE_URL = "https://api.freee.co.jp/api/1"


# ===== Notion: 稼働中エンジニア取得 =====


def get_active_engineers() -> list:
    """Notionから稼働状況=稼働中のエンジニアを取得"""
    url = f"https://api.notion.com/v1/databases/{NOTION_ENGINEER_DB_ID}/query"
    payload = {"filter": {"property": "稼働状況", "select": {"equals": "稼働中"}}, "page_size": 100}

    res = requests.post(url, headers=NOTION_HEADERS, json=payload)
    if res.status_code != 200:
        print(f"❌ Notion取得エラー: {res.status_code} {res.text}")
        return []

    engineers = []
    for page in res.json().get("results", []):
        props = page.get("properties", {})

        name_prop = props.get("名前", {}).get("title", [])
        name = name_prop[0]["text"]["content"] if name_prop else "未記載"

        price_prop = props.get("単価（万円）", {}).get("number")
        price = price_prop if price_prop else 0

        company_prop = props.get("所属会社", {}).get("rich_text", [])
        company = company_prop[0]["text"]["content"] if company_prop else "未記載"

        project_prop = props.get("稼働案件", {}).get("rich_text", [])
        project = project_prop[0]["text"]["content"] if project_prop else "稼働案件未記載"

        engineers.append(
            {"name": name, "price": price, "company": company, "project": project, "notion_id": page["id"]}
        )

    print(f"稼働中エンジニア: {len(engineers)}名取得")
    return engineers


# ===== Freee: 取引先 取得 or 作成 =====


def find_partner(company_name: str) -> int | None:
    url = f"{FREEE_BASE_URL}/partners"
    params = {"company_id": FREEE_COMPANY_ID, "keyword": company_name}
    res = requests.get(url, headers=FREEE_HEADERS, params=params)
    if res.status_code != 200:
        return None
    partners = res.json().get("partners", [])
    return partners[0]["id"] if partners else None


def create_partner(company_name: str) -> int | None:
    url = f"{FREEE_BASE_URL}/partners"
    payload = {"company_id": int(FREEE_COMPANY_ID), "name": company_name, "partner_type": "customer"}
    res = requests.post(url, headers=FREEE_HEADERS, json=payload)
    if res.status_code in (200, 201):
        pid = res.json()["partner"]["id"]
        print(f"  取引先新規作成: {company_name} (ID:{pid})")
        return pid
    print(f"  取引先作成エラー: {res.status_code} {res.text}")
    return None


def get_or_create_partner(company_name: str) -> int | None:
    pid = find_partner(company_name)
    return pid if pid else create_partner(company_name)


# ===== Freee: 請求書作成 =====


def create_invoice(engineer: dict, issue_date: date, due_date: date) -> bool:
    """
    Freeeに請求書をドラフト作成する。
    作成後はFreeeの画面で確認 → 手動で送付。
    """
    company_name = engineer["company"]
    name = engineer["name"]
    price_man = engineer["price"]
    project = engineer["project"]

    if price_man == 0:
        print(f"  スキップ: {name}（単価未登録）")
        return False

    price_yen = price_man * 10000
    partner_id = get_or_create_partner(company_name)
    if not partner_id:
        print(f"  エラー: {company_name} の取引先IDが取得できません")
        return False

    title = f"{issue_date.year}年{issue_date.month}月分 業務委託料（{name}様）"

    payload = {
        "company_id": int(FREEE_COMPANY_ID),
        "issue_date": issue_date.strftime("%Y-%m-%d"),
        "due_date": due_date.strftime("%Y-%m-%d"),
        "partner_id": partner_id,
        "invoice_status": "draft",
        "title": title,
        "description": f"案件: {project}",
        "invoice_lines": [
            {
                "name": f"業務委託料（{name}様）{issue_date.year}年{issue_date.month}月分",
                "quantity": 1,
                "unit_price": price_yen,
                "tax_code": 1,  # 10%消費税
                "type": "normal",
            }
        ],
    }

    res = requests.post(f"{FREEE_BASE_URL}/invoices", headers=FREEE_HEADERS, json=payload)
    if res.status_code in (200, 201):
        invoice_id = res.json()["invoice"]["id"]
        print(f"  ✅ {name} / {company_name} / {price_man}万円 → ドラフト作成 (ID:{invoice_id})")
        return True
    else:
        print(f"  ❌ {name} / {res.status_code} {res.text}")
        return False


# ===== メイン =====


def run(target_month: date | None = None):
    today = date.today()

    if target_month is None:
        # デフォルト: 翌月分
        target_month = today.replace(day=1) + relativedelta(months=1)

    issue_date = target_month.replace(day=1)
    due_date = issue_date + relativedelta(months=1) - relativedelta(days=1)

    print("=== Freee請求書自動生成 ===")
    print(f"請求対象月 : {target_month.year}年{target_month.month}月分")
    print(f"請求日     : {issue_date}")
    print(f"支払期限   : {due_date}")
    print()

    engineers = get_active_engineers()
    if not engineers:
        print("稼働中エンジニアが0名です。終了します。")
        return

    success = failed = 0
    for eng in engineers:
        print(f"処理中: {eng['name']} / {eng['company']} / {eng['price']}万円")
        if create_invoice(eng, issue_date, due_date):
            success += 1
        else:
            failed += 1

    print()
    print("=== 完了 ===")
    print(f"請求書作成: {success}件 / スキップ・エラー: {failed}件")
    print("Freeeのドラフト一覧で確認してから送付してください。")
    print("→ https://secure.freee.co.jp/invoices")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 特定月を指定: python freee_invoice.py 2026-06
        y, m = map(int, sys.argv[1].split("-"))
        run(target_month=date(y, m, 1))
    else:
        run()
