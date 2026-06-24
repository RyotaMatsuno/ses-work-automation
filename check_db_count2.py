import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_API_KEY") or config.get("NOTION_TOKEN", "")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
PROJ_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"


def count_db(db_id, label):
    total = 0
    payload = {"page_size": 100}
    while True:
        r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=headers, json=payload)
        d = r.json()
        total += len(d.get("results", []))
        if not d.get("has_more"):
            break
        payload["start_cursor"] = d["next_cursor"]
    print(f"{label}: {total}件")


count_db(ENG_DB, "エンジニアDB")
count_db(PROJ_DB, "案件DB")
