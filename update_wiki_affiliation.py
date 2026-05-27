import requests, sys
sys.stdout.reconfigure(encoding='utf-8')
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

content = f"""## {datetime.now().strftime('%Y-%m-%d')} 所属情報フィールド追加・pipeline_v1強化

### エンジニアDBスキーマ追加
- 所属会社（rich_text）
- 所属担当者名（rich_text）
- 所属メール（email）
→ Notion DB PATCHで追加済み

### webhook_server.py 修正
- classify_message()にaffiliation/contact_name/contact_emailの抽出を追加
- register_engineer()に3フィールドへの書き込みを追加
- git push → Renderに自動デプロイ済み

### pipeline_v1 強化
- fetcher.pyのnormalize_engineer()にaffiliation/contact_name/contact_emailを追加
- composer.pyは既にengineer["所属会社"]/["所属担当者名"]に対応済みだった
- skill_autofill.pyのJSONパースエラー修正（空レスポンス・markdown除去）

### watchdog タスク登録完了
- register_watchdog.batを管理者実行にて登録成功
- jobz-commandサーバーが落ちた場合、5分以内に自動再起動される

### 運用上の注意
- LINEからエンジニア登録時に「株式会社〇〇 田中さん」の形で所属を含めると
  所属会社・担当者名が自動でNotionに保存され、意向確認メール文に反映される
- 既存登録済みエンジニアは所属情報が空のため、重要エンジニアは手動でNotion更新推奨
"""

res = requests.patch(
    f"https://api.notion.com/v1/blocks/{WIKI_PAGE_ID}/children",
    headers=headers,
    json={"children": [{"object": "block", "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]}}]}
)
print(f"Notion Wiki: {res.status_code}")
