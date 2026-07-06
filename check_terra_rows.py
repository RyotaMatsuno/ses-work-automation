import gspread, sys, io
from google.oauth2.service_account import Credentials

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json',
    scopes=scopes
)
gc = gspread.authorize(creds)
sh = gc.open_by_key('1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI')

terra = sh.worksheet('TERRA')
t_all = terra.get_all_values()

# Show current rows to find insert position
print("=== TERRA 現在の行 ===")
header = t_all[3]
print(f"Header (Row4): {header[:10]}")
for i in range(4, len(t_all)):
    r = t_all[i]
    if len(r) > 3 and r[3]:
        print(f"  Row{i+1}: [{r[2]}] {r[3]} ({r[1]}/{r[0]})")
    elif len(r) > 0 and r[0]:
        print(f"  Row{i+1}: (section) {r[0]}")

print(f"\nTotal data rows: {len(t_all)}")
print(f"Columns: {len(header)}")
print(f"Full header: {header}")
