
import gspread
from google.oauth2.service_account import Credentials

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)
ws = ss.worksheet("フラップテック")

# 行14（合計行の前）に鶴川を挿入
ws.insert_row(["", "稼働中", "鶴川", "2026/5", "長期", "（確認中）"], index=14)
print("FT 行14: 鶴川 稼働中 2026/5 追加完了")

# 確認
data = ws.get_all_values()
for i, row in enumerate(data[3:13], start=4):
    print(f"  行{i}: {row[:4]}")
