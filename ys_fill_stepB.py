# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
import time

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

KEY = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1nSbYDRA9nzezksBDZacTpR4udEIhWOtixcwD7jTXLFk"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(KEY, scopes=SCOPES)
gc = gspread.authorize(creds)
ws = gc.open_by_key(SS_ID).worksheet("経験者用")
sh_api = build("sheets", "v4", credentials=creds)

# sheetId & rowCount
info = (
    sh_api.spreadsheets().get(spreadsheetId=SS_ID, fields="sheets(properties(title,sheetId,gridProperties))").execute()
)
sid = None
rc = 0
for sh in info["sheets"]:
    if sh["properties"]["title"] == "経験者用":
        sid = sh["properties"]["sheetId"]
        rc = sh["properties"]["gridProperties"]["rowCount"]
print(f"sheetId={sid} rowCount={rc}", flush=True)

reqs = []
if rc < 135:
    reqs.append(
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sid, "gridProperties": {"rowCount": 135}},
                "fields": "gridProperties.rowCount",
            }
        }
    )
# slot6テンプレ R87:AR97 (rows idx86-96, cols0-43) を 3箇所へコピペ
SRC = {"sheetId": sid, "startRowIndex": 86, "endRowIndex": 97, "startColumnIndex": 0, "endColumnIndex": 44}
for dst_top in [97, 108, 119]:  # R98, R109, R120
    reqs.append(
        {
            "copyPaste": {
                "source": SRC,
                "destination": {
                    "sheetId": sid,
                    "startRowIndex": dst_top,
                    "endRowIndex": dst_top + 11,
                    "startColumnIndex": 0,
                    "endColumnIndex": 44,
                },
                "pasteType": "PASTE_NORMAL",
                "pasteOrientation": "NORMAL",
            }
        }
    )
sh_api.spreadsheets().batchUpdate(spreadsheetId=SS_ID, body={"requests": reqs}).execute()
print(f"[COPYPASTE OK] slots 7-9 template created (reqs={len(reqs)})", flush=True)
time.sleep(1)


# slots 7-9 データ投入
def C(rng, val):
    return {"range": rng, "values": [[val]]}


data = []
slot_base = {7: 98, 8: 109, 9: 120}
MARK_COLS = ["AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI"]
projects = {
    7: dict(
        no="7",
        ji="2020.4",
        shi="2020.4",
        goukei="1ヶ月",
        gyoshu="自社研修",
        gengo="",
        dbos="Windows",
        fw="Excel / Word / PowerPoint",
        hosoku="社内研修\n・セキュリティ講習（情報セキュリティの重要性／報連相／セキュリティポイント等）\n・IT基礎知識講習\n・ビジネスマナー講習（電話対応／ビジネスメール／セキュリティインシデント等）\n・Excel講習（基礎操作／一般的な関数）",
    ),
    8: dict(
        no="8",
        ji="2018.4",
        shi="2020.3",
        goukei="2年",
        gyoshu="サービス",
        gengo="",
        dbos="Windows",
        fw="Excel",
        hosoku="某人材派遣会社（正社員）\n・携帯端末の販売\n・接客（インターネット環境・スマートフォン関連の知識を活用）",
    ),
    9: dict(
        no="9",
        ji="2016.3",
        shi="2018.3",
        goukei="2年1ヶ月",
        gyoshu="サービス",
        gengo="",
        dbos="Windows",
        fw="Excel",
        hosoku="某飲食店（契約社員）\n・店舗責任者\n・キッチン／フロア（接客）\n・売上・発注数の管理",
    ),
}
for i, p in projects.items():
    B = slot_base[i]
    data.append(C(f"A{B}", p["no"]))
    data.append(C(f"C{B + 3}", p["ji"]))
    data.append(C(f"C{B + 5}", p["shi"]))
    data.append(C(f"C{B + 7}", p["goukei"]))
    data.append(C(f"I{B}", p["hosoku"]))
    data.append(C(f"X{B + 5}", p["gyoshu"]))
    data.append(C(f"AJ{B + 5}", p["gengo"]))
    data.append(C(f"AM{B + 5}", p["dbos"]))
    data.append(C(f"AP{B + 5}", p["fw"]))
    for col in MARK_COLS:
        data.append(C(f"{col}{B + 5}", ""))  # 接客/研修=工程マーク無し
ws.batch_update(data, value_input_option="RAW")
print(f"[STEP B WRITE OK] {len(data)} cells", flush=True)
time.sleep(1)

# 検証
from gspread.utils import a1_to_rowcol

vals = ws.get_all_values()


def g(a1):
    r, c = a1_to_rowcol(a1)
    try:
        return vals[r - 1][c - 1]
    except:
        return "∅"


for i in [7, 8, 9]:
    B = slot_base[i]
    print(
        f"slot{i}: No={g(f'A{B}')} {g(f'C{B + 3}')}~{g(f'C{B + 5}')}({g(f'C{B + 7}')}) 業種={g(f'X{B + 5}')} OS={g(f'AM{B + 5}')} ツール={g(f'AP{B + 5}')[:20]} 補足頭={g(f'I{B}')[:16]!r}",
        flush=True,
    )
print("総行数(データ):", len(vals), flush=True)
print("[DONE]", flush=True)
