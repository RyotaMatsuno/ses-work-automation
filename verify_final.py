import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import gspread
from google.oauth2.service_account import Credentials

KEY = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(KEY, scopes=SCOPES)
gc = gspread.authorize(creds)

# 岡本共有シート確認
OKAMOTO_ID = '1UWU_X7U4kSUVrKrPp94JmL4CEE1g5V4k8PHcNbsqR-8'
sh = gc.open_by_key(OKAMOTO_ID)

for ws_name in ['2025年5月分', '2025年6月分', '2025年7月分']:
    ws = sh.worksheet(ws_name)
    data = ws.get_all_values()
    print(f"\n=== {ws_name} ===")
    for i, row in enumerate(data):
        cleaned = [c for c in row if c.strip()]
        if cleaned:
            print(f"  Row{i+1}: {row[:12]}")

# マスター鶴川備考確認
print("\n=== マスター鶴川備考 ===")
MASTER_ID = '1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI'
master = gc.open_by_key(MASTER_ID)
ft = master.worksheet('フラップテック')
row12 = ft.row_values(12)
print(f"  備考(col18): {row12[17]}")
