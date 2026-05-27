import requests, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
h = {"Authorization": f"Bearer {config['NOTION_API_KEY']}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

# 案件DBに6フィールド追加
payload = {
    "properties": {
        "提案中":   {"number": {"format": "number"}},
        "面談希望": {"number": {"format": "number"}},
        "NG":       {"number": {"format": "number"}},
        "合格":     {"number": {"format": "number"}},
        "成約":     {"number": {"format": "number"}},
        "営業終了": {"number": {"format": "number"}},
    }
}

res = requests.patch(
    "https://api.notion.com/v1/databases/343450ff-37c0-81e4-934e-f25f90284a3c",
    headers=h, json=payload
)
print(f"status: {res.status_code}")
if res.status_code == 200:
    print("フィールド追加OK: 提案中 / 面談希望 / NG / 合格 / 成約 / 営業終了")
else:
    print(res.text[:300])
