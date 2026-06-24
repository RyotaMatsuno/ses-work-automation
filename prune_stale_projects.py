import datetime
import os
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
cfg = dotenv_values(os.path.join(BASE, "config", ".env"))
KEY = cfg.get("NOTION_API_KEY")
DB = "343450ff-37c0-81e4-934e-f25f90284a3c"
H = {"Authorization": f"Bearer {KEY}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
PROG = os.path.join(BASE, "_prune_progress.txt")
IDS = os.path.join(BASE, "_prune_changed_ids.txt")


def log(m):
    with open(PROG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%H:%M:%S} {m}\n")


open(PROG, "w", encoding="utf-8").close()

cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
log(f"START prune cutoff(created_before)={cutoff} target_status=募集中 -> 終了")
flt = {
    "and": [
        {"property": "ステータス", "select": {"equals": "募集中"}},
        {"timestamp": "created_time", "created_time": {"before": cutoff}},
    ]
}
# READ PHASE
ids = []
cursor = None
pg = 0
while True:
    body = {"page_size": 100, "filter": flt}
    if cursor:
        body["start_cursor"] = cursor
    r = None
    for att in range(6):
        r = requests.post(f"https://api.notion.com/v1/databases/{DB}/query", headers=H, json=body, timeout=60)
        if r.status_code == 429:
            time.sleep(2 * (att + 1))
            continue
        break
    if r is None or r.status_code != 200:
        log(f"READ ERR {getattr(r, 'status_code', None)} {getattr(r, 'text', '')[:150]}")
        break
    d = r.json()
    ids += [x["id"] for x in d.get("results", [])]
    pg += 1
    if pg % 10 == 0:
        log(f"read pages={pg} ids={len(ids)}")
    if not d.get("has_more"):
        break
    cursor = d.get("next_cursor")
with open(IDS, "w", encoding="utf-8") as f:
    f.write("\n".join(ids))
log(f"READ DONE to_update={len(ids)} (これから終了ステータスへ更新)")
# UPDATE PHASE
done = err = 0
for pid in ids:
    body = {"properties": {"ステータス": {"select": {"name": "終了"}}}}
    ok = False
    for att in range(6):
        rr = requests.patch(f"https://api.notion.com/v1/pages/{pid}", headers=H, json=body, timeout=30)
        if rr.status_code == 429:
            time.sleep(2 * (att + 1))
            continue
        ok = rr.status_code == 200
        break
    done += 1 if ok else 0
    err += 0 if ok else 1
    if (done + err) % 100 == 0:
        log(f"updated={done} err={err} / {len(ids)}")
    time.sleep(0.34)
log(f"UPDATE DONE updated={done} err={err} total={len(ids)} 完了")
