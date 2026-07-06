import gspread
from google.oauth2.service_account import Credentials

scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json',
    scopes=scopes
)
gc = gspread.authorize(creds)
sh = gc.open_by_key('1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI')

# TERRA rows 36-45
terra = sh.worksheet('TERRA')
all_terra = terra.get_all_values()
print("=== TERRA rows 35-end ===")
for i in range(34, min(len(all_terra), 45)):
    row = all_terra[i]
    print(f"Row {i+1}: {row[:10]}")

# Income forecast sheet
print("\n=== 入金予測 worksheet ===")
yosoku = sh.worksheet('\u5165\u91d1\u4e88\u6e2c')
all_yosoku = yosoku.get_all_values()
for i, row in enumerate(all_yosoku, 1):
    print(f"Row {i}: {row[:11]}")
