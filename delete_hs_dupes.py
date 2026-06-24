import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8")
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
API_KEY = cfg.get("NOTION_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# 一番古い1件（2026-05-26）を残して他を削除
keep_id = "36c450ff-37c0-813b-8f31-d38228e3cf2e"  # 最古の1件
delete_ids = [
    "36e450ff-37c0-8139-89e8-dd504e18bdd9",
    "36e450ff-37c0-81ec-a252-d33dee1e409b",
    "36e450ff-37c0-8156-b0b1-eed7ca7e221e",
    "36e450ff-37c0-81ee-9c35-cd396e14c058",
    "36e450ff-37c0-8186-a987-caf59f7a20c0",
    "36e450ff-37c0-8151-bcfd-cc322240eef1",
    "36d450ff-37c0-81a5-8d69-fee3a59d346b",
    "36d450ff-37c0-818c-a926-dd42c780ace1",
    "36d450ff-37c0-817e-8b76-d4529b736ba1",
    "36d450ff-37c0-81c9-8fcc-cb8803f5aa77",
    "36d450ff-37c0-812e-977a-f092a6593a61",
    "36d450ff-37c0-81ba-927c-de5e0ff424d2",
    "36d450ff-37c0-810a-9622-dc2b323ca375",
    "36d450ff-37c0-8193-988a-e9b89c5c26ae",
    "36d450ff-37c0-81e8-b750-eb8938a263f0",
    "36c450ff-37c0-8189-a677-ffd56f9c70ad",  # 同日の2件目も削除
]

deleted = 0
errors = 0
for pid in delete_ids:
    r = requests.patch(f"https://api.notion.com/v1/pages/{pid}", headers=HEADERS, json={"in_trash": True}, timeout=15)
    if r.status_code in (200, 204):
        deleted += 1
    else:
        print(f"ERROR {r.status_code}: {pid}")
        errors += 1
    time.sleep(0.35)

print(f"削除: {deleted}件 / エラー: {errors}件")
print(f"残存: keep_id={keep_id} (2026-05-26)")
