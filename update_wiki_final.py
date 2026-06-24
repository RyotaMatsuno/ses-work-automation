import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
from datetime import datetime

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
headers = {
    "Authorization": f"Bearer {config['NOTION_API_KEY']}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

content = f"""{datetime.now().strftime("%Y-%m-%d")} 残タスク完了・運用設計確定

■ cleanup_v2.py → 完了済み確認（エンジニアDB 15件、全2026-05-11以降）

■ LINE通知スケジュール再設計
- 月200通制限対策として notify_line.py を毎日→週2回（月・木 9:00）に変更
- タスク: jobz_notify_weekly 登録済み
- run_matching_and_notify.bat: マッチングのみに変更（notify分離）
- 手動確認: LINEに「マッチング」と送ればReply APIで即返答（無制限）

■ 運用方針確定
- LINEの意向確認通知: 所属会社名不要（候補名＋案件名のみ）
- outreach_system: 新営業アドレス発行待ちで保留
- 岡本LINE Webhook: 岡本からURL受領待ち

■ 残タスク
- 6/1以降: notify_line.py本番テスト（月リセット後）
- 新営業アドレス発行後: outreach_systemの.envにOUTREACH_FROM_EMAILを追加して本番運用開始
- 岡本LINE設定: 岡本からWebhook URL受領後にジョブズが即反映
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
print(f"Wiki: {res.status_code}")
