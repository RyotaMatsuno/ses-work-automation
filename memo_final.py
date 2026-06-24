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

content = f"""{datetime.now().strftime("%Y-%m-%d")} 未実装タスク 全3件完了

■ ① 返信自動解析（reply_parser/reply_parser.py）
  - 並行スコア自動計算（判断マニュアルv3 §5準拠）
  - 必須/尚可スキル○×抽出（Claude API + regex フォールバック）
  - 提案可否判定 → Notion エンジニアDBに自動書き込み
  - dry-run smoke test: RC=0 確認

■ ② 請求書自動送付（freee/invoice_sender.py）
  - freee API で当月confirmed請求書取得
  - PDF ダウンロード → SMTP でクライアントへ自動送付
  - 送付先不明時は LINE で松野に通知
  - スケジューラ: 毎月1日 10:00（register_invoice_sender_task.bat で登録 / 管理者権限必要）
  - dry-run smoke test: RC=0 確認

■ ③ 入金確認自動化（freee/payment_checker.py）
  - freee API で入金ステータス確認
  - 支払期日超過・未入金 → 松野 LINE に Push 通知
  - 通知済みフラグで重複防止（logs/payment_notified.json）
  - スケジューラ: 毎月 10日・20日・28日 08:00（register_payment_check_task.bat で登録 / 管理者権限必要）
  - dry-run smoke test: RC=0 確認

■ 残タスク（松野の手動作業）
  - freee_invoice_send タスク登録: register_invoice_sender_task.bat を管理者で実行
  - freee_payment_check タスク登録: register_payment_check_task.bat を管理者で実行
  - アポ取りシステム: 保留中
  - 岡本 LINE Webhook: 催促済み、完了連絡待ち
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
