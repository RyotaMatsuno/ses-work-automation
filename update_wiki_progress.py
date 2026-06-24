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

content = f"""{datetime.now().strftime("%Y-%m-%d")} 案件進捗管理システム実装完了

■ Notion案件DBフィールド追加
  提案中 / 面談希望 / NG / 合格 / 成約 / 営業終了（number型）
  TechBiz Scout（https://scout.techbiz.com）と同じ案件ベース管理

■ LINEコマンド追加（Reply API・無制限）
  「進捗」と送る → 募集中・選考中案件の提案状況をReply APIで返信
  数字が入っている案件のみ表示（全部0はスキップ）

■ daily_report.py 新規作成
  毎朝8時にPush APIで進捗サマリーを自動送信（jobz_daily_reportタスク登録済み）
  数字が入っている案件のみ表示 + 面談希望ありは⚡要アクション欄に表示
  全部0なら「要アクション: なし」のみ送信（1通/日で月30通以内）

■ 運用方法
  Notionで案件に「提案中:2」「面談希望:1」など数字を入力するだけで
  翌朝8時の通知とLINEの「進捗」コマンド両方に反映される
  webhook_server.py → git push → Renderに自動デプロイ済み

■ タスク一覧（現在稼働中）
  jobz_matching_daily: 毎日8時 マッチング実行
  jobz_notify_weekly: 月・木 9時 マッチング結果LINE通知
  jobz_daily_report: 毎日8時 案件進捗通知
  jobz-watchdog: 5分おき jobz-commandサーバー監視
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
