
import gspread, json
from google.oauth2.service_account import Credentials

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)

# 全シートのデータをJSON化
all_data = {}
for sname in ["TERRA", "フラップテック", "グレイスライン", "入金予測"]:
    ws = ss.worksheet(sname)
    data = ws.get_all_values()
    all_data[sname] = [{"row": i+1, "data": row} for i, row in enumerate(data) if any(row)]

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\all_sheets.json", "w", encoding="utf-8") as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)

# TERRAの支払いサイト確認（I列=index8）
print("=== TERRA 支払いサイト ===")
for row_info in all_data["TERRA"]:
    row = row_info["data"]
    if row_info["row"] < 5: continue
    name = row[3].strip() if len(row) > 3 else ""
    status = row[2].strip() if len(row) > 2 else ""
    site = row[8].strip() if len(row) > 8 else ""
    if name and name not in ("氏名", "稼働中合計") and "稼働中" in status:
        print(f"  {name}: サイト{site}日")

print("\n=== FT 支払いサイト ===")
for row_info in all_data["フラップテック"]:
    row = row_info["data"]
    if row_info["row"] < 4: continue
    name = row[2].strip() if len(row) > 2 else ""
    status = row[1].strip() if len(row) > 1 else ""
    site = row[12].strip() if len(row) > 12 else ""
    if name and name not in ("氏名", "稼働中合計") and "稼働中" in status:
        print(f"  {name}: サイト{site}日")

print("\n=== GL 支払いサイト ===")
for row_info in all_data["グレイスライン"]:
    row = row_info["data"]
    if row_info["row"] < 4: continue
    name = row[1].strip() if len(row) > 1 else ""
    status = row[0].strip() if len(row) > 0 else ""
    site = row[10].strip() if len(row) > 10 else ""
    if name and name not in ("氏名", "稼働中合計") and "稼働中" in status:
        print(f"  {name}: サイト{site}")
