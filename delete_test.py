import requests
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = env["NOTION_API_KEY"]

page_id = "36c450ff-37c0-81c5-9296-d0aa4ae83011"
res = requests.patch(
    f"https://api.notion.com/v1/pages/{page_id}",
    headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"},
    json={"archived": True},
)
print(res.status_code, res.json().get("id", res.text[:100]))
