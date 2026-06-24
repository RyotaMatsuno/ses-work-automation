# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from gspread.utils import rowcol_to_a1

KEY = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1nSbYDRA9nzezksBDZacTpR4udEIhWOtixcwD7jTXLFk"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(KEY, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)
ws = ss.worksheet("経験者用")

# 書き込み権限チェック
drive = build("drive", "v3", credentials=creds)
meta = drive.files().get(fileId=SS_ID, fields="name,capabilities(canEdit)").execute()
print(f"file={meta['name']}  canEdit={meta['capabilities']['canEdit']}", flush=True)

# 正確なA1座標でダンプ（スキルマトリクス + 自己PR領域 = R1-R29）
vals = ws.get_all_values()
print(f"total_rows={len(vals)}", flush=True)
print("=== R1-R29 (実A1アドレス) ===", flush=True)
for r in range(min(29, len(vals))):
    row = vals[r]
    cells = []
    for c, v in enumerate(row):
        if str(v).strip():
            cells.append(f"{rowcol_to_a1(r + 1, c + 1)}={v!r}")
    if cells:
        print(f"R{r + 1}: " + " | ".join(cells), flush=True)

# 結合セル（R1-R29範囲）
sh_api = build("sheets", "v4", credentials=creds)
info = sh_api.spreadsheets().get(spreadsheetId=SS_ID, fields="sheets(properties(title),merges)").execute()
for sh in info["sheets"]:
    if sh["properties"]["title"] == "経験者用":
        merges = sh.get("merges", [])
        rel = [m for m in merges if m.get("startRowIndex", 0) < 29]
        print(f"\n=== 結合セル (R1-29のみ / 全{len(merges)}件中{len(rel)}件) ===", flush=True)
        for m in rel:
            tl = rowcol_to_a1(m["startRowIndex"] + 1, m["startColumnIndex"] + 1)
            br = rowcol_to_a1(m["endRowIndex"], m["endColumnIndex"])
            print(f"  {tl}:{br}", flush=True)
print("\n[DONE]", flush=True)
