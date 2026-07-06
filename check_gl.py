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

# Check GL column (col G = col 7) for all data rows
rows_to_check = [5,6,7, 10,11,12, 15,16,17, 20,21,22]
labels = ['6/15','6/末','6小計', '7/15','7/末','7小計', '8/15','8/末','8小計', '9/15','9/末','9小計']

print("Row  Label    GL(col7)")
for r, lab in zip(rows_to_check, labels):
    val = yosoku.cell(r, 7).value
    print(f"  {r:>2}  {lab:<6}  {val}")
