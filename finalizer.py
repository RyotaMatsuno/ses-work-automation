import datetime
import os
import subprocess
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
REP = os.path.join(BASE, "_finalizer_report.txt")


def rep(m):
    with open(REP, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%H:%M:%S} {m}\n")


open(REP, "w", encoding="utf-8").close()
rep("FINALIZER START - waiting for prune UPDATE DONE")

# 1. wait for prune completion (max 90 min)
done = False
for _ in range(180):  # 180*30s = 90min
    try:
        txt = open(PROG, encoding="utf-8", errors="replace").read()
    except:
        txt = ""
    if "UPDATE DONE" in txt:
        done = True
        rep("prune finished: " + txt.strip().splitlines()[-1])
        break
    if "READ ERR" in txt:
        rep("prune READ ERR detected -> abort finalizer (v3 left DISABLED)")
        break
    time.sleep(30)
if not done:
    rep("prune NOT done within 90min OR error -> v3 left DISABLED, manual check needed")
    raise SystemExit(0)

# 2. recount 募集中
cnt = 0
cursor = None
pages = 0
flt = {"property": "ステータス", "select": {"equals": "募集中"}}
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
    if not r or r.status_code != 200:
        rep(f"recount query err {getattr(r, 'status_code', None)}")
        break
    d = r.json()
    cnt += len(d.get("results", []))
    pages += 1
    if not d.get("has_more"):
        break
    cursor = d.get("next_cursor")
rep(f"募集中 件数(プルーニング後)= {cnt} (pages={pages})")

# 3. re-enable matching_v3
e = subprocess.run(
    ["schtasks", "/change", "/tn", "SES_MatchingV3", "/enable"],
    capture_output=True,
    text=True,
    encoding="cp932",
    errors="replace",
)
rep(f"SES_MatchingV3 re-enable rc={e.returncode}")
q = subprocess.run(
    ["schtasks", "/query", "/tn", "SES_MatchingV3", "/fo", "list"],
    capture_output=True,
    text=True,
    encoding="cp932",
    errors="replace",
)
for line in (q.stdout or "").splitlines():
    if "Status" in line or "状態" in line or "Next" in line or "次回" in line:
        rep("  v3 " + line.strip()[:100])
rep("FINALIZER DONE")
print("finalizer logic complete (this print only if run sync; normally launched detached)")
