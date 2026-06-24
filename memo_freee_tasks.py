import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
headers = {
    "Authorization": f"Bearer {config['NOTION_API_KEY']}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

content = f"""{datetime.now().strftime("%Y-%m-%d")} freeeタスクスケジューラ自動登録完了

■ 登録済みタスク（全て稼働中）
  freee_auto_invoice      毎月1日  09:00  請求書自動生成（既存）
  freee_invoice_send      毎月1日  10:00  請求書自動送付（新規）
  freee_payment_check     毎月10日 08:00  入金確認（新規）
  freee_payment_check_20  毎月20日 08:00  入金確認（新規）
  freee_payment_check_28  毎月28日 08:00  入金確認（新規）

■ 経理フロー 完全自動化
  毎月1日: 請求書生成 → 1時間後に自動送付
  毎月10・20・28日: 未入金チェック → 期日超過あれば松野LINEに通知

■ 松野の経理作業 = ゼロ（入金確認通知を受け取るだけ）
"""

res = requests.patch(
    "https://api.notion.com/v1/blocks/353450ff-37c0-8145-9e3e-d80c8c8ed594/children",
    headers=headers,
    json={
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]},
            }
        ]
    },
)
print(f"Notion Wiki: {res.status_code}")
