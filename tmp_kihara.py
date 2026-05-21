
import gspread, json
from google.oauth2.service_account import Credentials

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)

# GL: 木原さん分 = P列(index14)
ws_gl = ss.worksheet("グレイスライン")
data_gl = ws_gl.get_all_values()
print("=== GL 木原さん分 ===")
for i, row in enumerate(data_gl[3:], start=4):
    if not row[1].strip(): continue
    name = row[1].strip()
    status = row[0].strip()
    kihara = row[14].strip() if len(row) > 14 else ""
    if status in ("退場済み","退場前"): continue
    print(f"  {name}: {kihara}")

# FT: 木原さん分 = P列(index15)
ws_ft = ss.worksheet("フラップテック")
data_ft = ws_ft.get_all_values()
print("=== FT 木原さん分 ===")
for i, row in enumerate(data_ft[3:], start=4):
    if not row[2].strip(): continue
    name = row[2].strip()
    status = row[1].strip()
    kihara = row[15].strip() if len(row) > 15 else ""
    if status in ("5月末終了","退場済み"): continue
    print(f"  {name}: {kihara}")
