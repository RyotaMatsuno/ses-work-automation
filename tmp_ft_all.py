
import gspread, json
from google.oauth2.service_account import Credentials

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)
ws = ss.worksheet("フラップテック")
data = ws.get_all_values()

out = [{"row": i+1, "data": row[:6]} for i, row in enumerate(data)]
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ft_all.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"FT全行: {len(data)}行")
