# -*- coding: utf-8 -*-
"""mail_pipeline取り込み状況サマリー"""

import json
import re
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from collections import defaultdict
from datetime import datetime, timedelta

from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
DB_PROJ = "343450ff-37c0-81e4-934e-f25f90284a3c"
DB_ENG = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

# 1. processed_ids数
print("=== 1. processed_ids ===")
pid_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\processed_ids.json"
with open(pid_path, "r", encoding="utf-8") as f:
    pids = json.load(f)
if isinstance(pids, list):
    print(f"  processed_ids: {len(pids)}件（旧形式list）")
elif isinstance(pids, dict):
    total = sum(len(v) for v in pids.values())
    print(f"  processed_ids total: {total}件")
    for k, v in pids.items():
        print(f"    {k}: {len(v)}件")

# 2. pipeline.py設定値
print("\n=== 2. pipeline設定値 ===")
pp = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"
with open(pp, "r", encoding="utf-8") as f:
    for line in f:
        if re.match(r"^(FETCH_LIMIT|PROCESS_LIMIT|DAILY_COST_LIMIT_USD)\s*=", line):
            print(f"  {line.strip()}")

# 3. 案件DB件数
print("\n=== 3. 案件DB件数 ===")
url = f"https://api.notion.com/v1/databases/{DB_PROJ}/query"
status_count = defaultdict(int)
total_proj = 0
cursor = None
while True:
    body = {"page_size": 100}
    if cursor:
        body["start_cursor"] = cursor
    r = requests.post(url, headers=HEADERS, json=body, timeout=30)
    data = r.json()
    for rec in data.get("results", []):
        total_proj += 1
        props = rec.get("properties", {})
        st = ""
        for k, v in props.items():
            if "ステータス" in k:
                sel = v.get("select") or v.get("status")
                if sel:
                    st = sel.get("name", "")
        status_count[st] += 1
    if not data.get("has_more"):
        break
    cursor = data.get("next_cursor")
print(f"  案件DB total: {total_proj}件")
for s, c in sorted(status_count.items(), key=lambda x: -x[1]):
    print(f"    {s or '(空)': <15}: {c}件")

# 4. エンジニアDB件数
print("\n=== 4. エンジニアDB件数 ===")
url2 = f"https://api.notion.com/v1/databases/{DB_ENG}/query"
eng_count = 0
eng_status = defaultdict(int)
cursor = None
while True:
    body = {"page_size": 100}
    if cursor:
        body["start_cursor"] = cursor
    r = requests.post(url2, headers=HEADERS, json=body, timeout=30)
    data = r.json()
    for rec in data.get("results", []):
        eng_count += 1
        props = rec.get("properties", {})
        for k, v in props.items():
            if "稼働状況" in k:
                sel = v.get("select")
                if sel:
                    eng_status[sel.get("name", "")] += 1
    if not data.get("has_more"):
        break
    cursor = data.get("next_cursor")
print(f"  エンジニアDB total: {eng_count}件")
for s, c in sorted(eng_status.items(), key=lambda x: -x[1]):
    print(f"    {s or '(空)': <15}: {c}件")

# 5. 日別登録数（案件DB created_time集計 直近7日）
print("\n=== 5. 案件DB 日別新規登録数（直近7日） ===")
since7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00.000Z")
url3 = f"https://api.notion.com/v1/databases/{DB_PROJ}/query"
day_count = defaultdict(int)
cursor = None
while True:
    body = {"filter": {"timestamp": "created_time", "created_time": {"on_or_after": since7}}, "page_size": 100}
    if cursor:
        body["start_cursor"] = cursor
    r = requests.post(url3, headers=HEADERS, json=body, timeout=30)
    data = r.json()
    for rec in data.get("results", []):
        ct = rec.get("created_time", "")[:10]
        day_count[ct] += 1
    if not data.get("has_more"):
        break
    cursor = data.get("next_cursor")
for d in sorted(day_count.keys()):
    print(f"    {d}: {day_count[d]}件")

# 6. メールボックス総数（参考）
print("\n=== 6. IMAP総メール数（参考） ===")
import imaplib

IMAP_HOST = "mail65.onamae.ne.jp"
for addr, pw_key in [
    ("sessales@terra-ltd.co.jp", "SESSALES_PASSWORD"),
    ("r-matsuno@terra-ltd.co.jp", "MATSUNO_PASSWORD"),
    ("r-okamoto@terra-ltd.co.jp", "OKAMOTO_PASSWORD"),
]:
    pw = env.get(pw_key)
    if not pw:
        print(f"  {addr}: pw not found")
        continue
    try:
        M = imaplib.IMAP4_SSL(IMAP_HOST, 993, timeout=15)
        M.login(addr, pw)
        M.select("INBOX", readonly=True)
        typ, data = M.search(None, "ALL")
        total = len(data[0].split()) if data[0] else 0
        # 直近3日
        since3 = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
        typ2, data2 = M.search(None, f"(SINCE {since3})")
        recent = len(data2[0].split()) if data2[0] else 0
        print(f"  {addr}: 総{total}件 / 直近3日{recent}件")
        M.logout()
    except Exception as e:
        print(f"  {addr}: {e}")
