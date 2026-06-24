import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SA_FILE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json"

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(SA_FILE, scopes=scopes)
gc = gspread.authorize(creds)
sh = gc.open_by_key(SPREADSHEET_ID)

# GLシート
gl = sh.worksheet("グレイスライン")
gl_vals = gl.get_all_values()
print("=== GL シート ===")
for i, row in enumerate(gl_vals):
    print(f"行{i + 1}: {row}")

# FTシート
ft = sh.worksheet("フラップテック")
ft_vals = ft.get_all_values()
print("\n=== FT シート ===")
for i, row in enumerate(ft_vals):
    print(f"行{i + 1}: {row}")
