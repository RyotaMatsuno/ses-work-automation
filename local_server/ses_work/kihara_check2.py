import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SA_FILE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json"

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(SA_FILE, scopes=scopes)
gc = gspread.authorize(creds)
sh = gc.open_by_key(SPREADSHEET_ID)

gl = sh.worksheet("グレイスライン")
gl_vals = gl.get_all_values()

print("=== GL 全稼働者（退場済み含む）===")
for i, row in enumerate(gl_vals):
    if i < 3:
        continue
    if any(row):
        print(f"行{i + 1}: ステータス={row[0]} 氏名={row[1]} 参画={row[2]} 期間={row[3]} 木原分={row[14]}")

ft = sh.worksheet("フラップテック")
ft_vals = ft.get_all_values()

print("\n=== FT 全稼働者（退場済み含む）===")
for i, row in enumerate(ft_vals):
    if i < 3:
        continue
    if any(row):
        print(f"行{i + 1}: ステータス={row[1]} 氏名={row[2]} 参画={row[3]} 期間={row[4]} 木原分={row[15]}")
