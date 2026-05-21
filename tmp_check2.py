
import gspread, json
from google.oauth2.service_account import Credentials

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)

for sname in ["フラップテック", "グレイスライン"]:
    ws = ss.worksheet(sname)
    data = ws.get_all_values()
    out = [{"row": i+1, "cols": row[:6]} for i, row in enumerate(data) if any(row)]
    with open(f"C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work\\sheets_{sname}.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"{sname}: {len(out)}行")
