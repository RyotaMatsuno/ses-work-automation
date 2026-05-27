import requests
from dotenv import dotenv_values
from datetime import datetime

ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
config = dotenv_values(ENV_PATH)
NOTION_API_KEY = config["NOTION_API_KEY"]
WIKI_PAGE_ID = "353450ff-37c0-8145-9e3e-d80c8c8ed594"

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

today = datetime.now().strftime("%Y-%m-%d")

content = f"""## {today} 実装完了: pipeline_v1 / outreach_system

### 完了したシステム

**pipeline_v1（Phase1営業パイプライン）**
- パス: `ses_work/pipeline_v1/`
- 機能: Notion案件DBの募集中案件×稼働可能エンジニアをマッチングし、意向確認メール文を自動生成
- 実行: `python pipeline.py --dry-run`
- 結果: result_pipeline.json に出力
- 動作確認: 案件4件取得、マッチング1件成功

**outreach_system（アポ取りシステム）**
- パス: `ses_work/outreach_system/`
- 機能: targets.csvの送信先リストにテンプレートA/Bメールを一括送信（180日再送制御・断り除外）
- 実行: `python outreach.py --dry-run`（本番: `--run`）
- 送信元: OUTREACH_FROM_EMAIL（未設定時は松野アドレスでフォールバック）
- 動作確認: 3件中2件dry-run成功、1件断り除外OK

### 注意事項
- outreach_systemの本番送信前にtargets.csvに実際の送信先を入れること
- .envにOUTREACH_FROM_EMAIL/OUTREACH_MAIL_PASSWORDを設定すると送信元アドレスを変更可能
- pipeline_v1は現在dry-runのみ。本番LINEへの通知はnotify_line.pyと統合して実装予定

### 未完了
- watchdog タスクスケジューラ登録（管理者権限必要 → 松野が手動で `register_watchdog.bat` を管理者実行）
"""

blocks = [
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": content}}]
        }
    }
]

res = requests.patch(
    f"https://api.notion.com/v1/blocks/{WIKI_PAGE_ID}/children",
    headers=headers,
    json={"children": blocks}
)
print(f"status: {res.status_code}")
if res.status_code != 200:
    print(res.text[:300])
else:
    print("Notion Wiki updated OK")
