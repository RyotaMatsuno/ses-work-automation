import gspread
from google.oauth2.service_account import Credentials

scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json',
    scopes=scopes
)
gc = gspread.authorize(creds)
sh = gc.open_by_key('1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI')

# TERRA worksheet
terra = sh.worksheet('TERRA')
all_vals = terra.get_all_values()
print("=== TERRA worksheet ===")
for i, row in enumerate(all_vals, 1):
    # Show row number and key columns (cols A-H, plus col S for memo)
    name_col = row[3] if len(row) > 3 else ''
    status_col = row[2] if len(row) > 2 else ''
    if name_col or status_col or i <= 2:
        print(f"Row {i}: [{row[0]}] [{row[1]}] [{row[2]}] [{row[3]}] [{row[4]}] [{row[5]}] [{row[6]}] [{row[7]}] [{row[8]}]")

print("\n=== Header row details ===")
if all_vals:
    for j, col in enumerate(all_vals[0]):
        print(f"  Col {j} ({chr(65+j) if j < 26 else ''}): {col}")
