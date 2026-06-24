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

content = f"""{datetime.now().strftime("%Y-%m-%d")} 未実装タスク実装進捗

■ 完了
  返信自動解析（reply_parser/reply_parser.py）
  - Claude API + 正規表現フォールバックで返信メール本文を解析
  - 並行スコア計算（判断マニュアルv3 §5準拠）
  - 必須/尚可スキル○×抽出
  - 提案可否判定（スコア5.0未満AND必須全○→OK）
  - dry-run smoke test: 並行スコア3.0・提案可否OK → 正常動作確認
  - Notion更新: エンジニアDBの並行スコア/スキル判定メモ/提案可否/最終更新日

■ 実装中（Codex稼働中）
  請求書自動送付（freee/invoice_sender.py）
  - freee API疎通確認済み（トークンリフレッシュ正常）
  - CLAUDE.md / SPEC.md / TASKS.md 作成済み
  - Codexが実装中

■ 未着手（次）
  入金確認自動化（freee API連携）

■ アポ取りシステム → 保留（松野判断）

■ 岡本依頼事項（催促済み）
  LINE Webhook URL設定完了を松野経由で催促
  完了連絡次第ジョブズが即反映
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
