from dotenv import dotenv_values
import requests, json

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
headers = {
    "Authorization": f"Bearer {config['NOTION_API_KEY']}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

r = requests.post(
    "https://api.notion.com/v1/databases/343450ff-37c0-819d-8769-fb0a8a4ceeb1/query",
    headers=headers,
    json={"page_size": 1},
    timeout=20
)

with open("db_check.txt", "w", encoding="utf-8") as f:
    f.write(f"status: {r.status_code}\n")
    if r.ok:
        data = r.json()
        f.write(f"has_more: {data.get('has_more')}\n")
        f.write(f"results: {len(data.get('results', []))}\n")
    else:
        f.write(r.text[:500])

print("done")
