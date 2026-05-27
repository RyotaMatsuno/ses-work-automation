import requests, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values
from datetime import datetime

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
headers = {"Authorization": f"Bearer {config['NOTION_API_KEY']}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

content = f"""{datetime.now().strftime('%Y-%m-%d')} 全体像まとめ・方針確定

■ 自動化済み（ノータッチでOK）
  - メール受信→Notion DB登録（mail_pipeline v4.1 / 30分おき）
  - AIマッチング（matching_v2 / 毎日08:00 / 単価フィルタ追加済み）
  - LINE通知（月・木09:00 マッチング結果 / 毎日08:00 進捗）
  - freee請求書生成（毎月1日09:00）
  - インフラ監視（watchdog 5分おき）
  - LINEコマンド：マッチング / 進捗 / 更新（Reply API・無制限）

■ 松野が確認して送るだけの状態
  - 提案メール：drafts/に47件生成済み

■ アポ取りシステム → 一旦保留（松野判断）

■ 岡本依頼中（ブロッカー）
  - LINE Webhook URL設定
  - 完了連絡もらえればジョブズが即反映

■ 未実装 実装順
  1. 返信自動解析（並行スコア自動計算）→ 実装着手
  2. 請求書自動送付（freee PDF→メール）→ 次
  3. 入金確認自動化（freee API連携）→ その次

■ 岡本への催促
  - 松野公式LINEから送付予定（催促文生成済み）
"""

res = requests.patch(
    "https://api.notion.com/v1/blocks/353450ff-37c0-8145-9e3e-d80c8c8ed594/children",
    headers=headers,
    json={"children": [{"object": "block", "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]}}]}
)
print(f"Notion Wiki: {res.status_code}")
