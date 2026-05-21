
import gspread
from google.oauth2.service_account import Credentials
import json

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)

# TERRAシートの全データをJSONで出力（行番号付き）
ws = ss.worksheet("TERRA")
data = ws.get_all_values()
result = []
for i, row in enumerate(data, start=1):
    if any(row):
        result.append({"row": i, "cols": row[:8]})

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sheets_terra.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("done:", len(result), "rows")
