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
ws = gc.open_by_key(SS_ID).worksheet("経験者用")

vals = ws.get_all_values()
print(f"total_rows={len(vals)}", flush=True)
print("=== 業務実績表 R30-95 非空セル(実A1) ===", flush=True)
for r in range(29, min(95, len(vals))):
    row = vals[r]
    cells = []
    for c, v in enumerate(row):
        s = str(v).strip()
        if s:
            disp = s.replace("\n", "⏎")
            if len(disp) > 22:
                disp = disp[:22] + "…"
            cells.append(f"{rowcol_to_a1(r + 1, c + 1)}={disp!r}")
    if cells:
        print(f"R{r + 1}: " + " | ".join(cells), flush=True)

# 結合セル（R30-95）
sh_api = build("sheets", "v4", credentials=creds)
info = sh_api.spreadsheets().get(spreadsheetId=SS_ID, fields="sheets(properties(title,sheetId),merges)").execute()
for sh in info["sheets"]:
    if sh["properties"]["title"] == "経験者用":
        sid = sh["properties"]["sheetId"]
        merges = sh.get("merges", [])
        rel = [m for m in merges if 29 <= m.get("startRowIndex", 0) < 95]
        print(f"\nsheetId={sid}", flush=True)
        print(f"=== 結合 R30-95 ({len(rel)}件) ===", flush=True)
        # スロット1相当(R32-42)の構造を詳しく見るため行ごとに整理
        from collections import defaultdict

        byrow = defaultdict(list)
        for m in rel:
            tl = rowcol_to_a1(m["startRowIndex"] + 1, m["startColumnIndex"] + 1)
            br = rowcol_to_a1(m["endRowIndex"], m["endColumnIndex"])
            byrow[m["startRowIndex"] + 1].append(f"{tl}:{br}")
        for rr in sorted(byrow):
            print(f"  R{rr}: " + " | ".join(sorted(byrow[rr], key=lambda x: (len(x), x))), flush=True)
print("\n[DONE]", flush=True)
