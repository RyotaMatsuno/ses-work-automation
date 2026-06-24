import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SERVICE_ACCOUNT_FILE = "freee_auth/service_account.json"

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
gc = gspread.authorize(creds)

sh = gc.open_by_key(SPREADSHEET_ID)

# 全シート名確認
for ws in sh.worksheets():
    print(ws.title)
