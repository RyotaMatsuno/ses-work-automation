# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
import json

import gspread
from google.oauth2.service_account import Credentials

ORIG = "1nSbYDRA9nzezksBDZacTpR4udEIhWOtixcwD7jTXLFk"
FMT = "1TyKVdrwzUdURam5v9HG4A_RhyKJUhDmX"

# 候補となるSA鍵を総当たりで確認
import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
keys = [
    os.path.join(base, "google_credentials.json"),
    os.path.join(base, "config", "service_account.json"),
    os.path.join(base, "sheets_terra.json"),
]
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

for k in keys:
    if not os.path.exists(k):
        print(f"[skip] {k} なし", flush=True)
        continue
    try:
        with open(k, encoding="utf-8") as f:
            email = json.load(f).get("client_email")
        creds = Credentials.from_service_account_file(k, scopes=SCOPES)
        gc = gspread.authorize(creds)
        print(f"\n### 鍵: {os.path.basename(k)}  ({email})", flush=True)
        for label, key in [("元", ORIG), ("FMT", FMT)]:
            try:
                ss = gc.open_by_key(key)
                print(f"  [{label}] OPEN OK -> {ss.title} / タブ {[w.title for w in ss.worksheets()]}", flush=True)
            except Exception as e:
                print(f"  [{label}] NG: {str(e)[:120]}", flush=True)
    except Exception as e:
        print(f"[err] {k}: {str(e)[:120]}", flush=True)
print("\n[DONE]", flush=True)
