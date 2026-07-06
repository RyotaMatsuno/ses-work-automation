import gspread
from google.oauth2.service_account import Credentials

scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json',
    scopes=scopes
)
gc = gspread.authorize(creds)
sh = gc.open_by_key('1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI')
yosoku = sh.worksheet('\u5165\u91d1\u4e88\u6e2c')

# Fix annual total 総実入り (Row 64, col L = col 12)
yosoku.update_cell(64, 12, 10430008)
print("[OK] Row 64 総実入り fixed: 9,770,008 -> 10,430,008")

# Final verification
row64 = yosoku.row_values(64)
print(f"Row 64 final: {row64}")
