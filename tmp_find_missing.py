
import gspread, json, sys
from google.oauth2.service_account import Credentials

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)

result = {}

# --- TERRA: G=単価(8列目=index7), N=仕入単価(index13) ---
ws = ss.worksheet("TERRA")
data = ws.get_all_values()
terra_issues = []
for i, row in enumerate(data[4:], start=5):
    if not any(row[:6]): continue
    name = row[3].strip() if len(row) > 3 else ""
    status = row[2].strip() if len(row) > 2 else ""
    kubun = row[1].strip() if len(row) > 1 else ""
    tantou = row[0].strip()
    tanka = row[7].strip() if len(row) > 7 else ""
    shiire = row[13].strip() if len(row) > 13 else ""
    # ヘッダー・合計行除外
    if name in ("", "氏名", "稼働中合計"): continue
    if status in ("5月末終了", "退場済み", "退場前"): continue
    # BP行: 仕入単価が空
    if kubun == "BP" and not shiire:
        terra_issues.append({"row": i, "name": name, "status": status, "tantou": tantou, "kubun": kubun, "tanka": tanka, "shiire": shiire})
    # P行: 単価が空
    elif kubun == "P" and not tanka:
        terra_issues.append({"row": i, "name": name, "status": status, "tantou": tantou, "kubun": kubun, "tanka": tanka, "shiire": shiire})

result["TERRA_issues"] = terra_issues

# --- FT: G=案件単価(index6), H=仕入単価(index7) ---
ws_ft = ss.worksheet("フラップテック")
data_ft = ws_ft.get_all_values()
ft_issues = []
for i, row in enumerate(data_ft[3:], start=4):
    if not any(row[:5]): continue
    name = row[2].strip() if len(row) > 2 else ""
    status = row[1].strip() if len(row) > 1 else ""
    tanka = row[6].strip() if len(row) > 6 else ""
    shiire = row[7].strip() if len(row) > 7 else ""
    if name in ("", "氏名", "稼働中合計"): continue
    if status in ("5月末終了", "退場済み"): continue
    if not tanka or not shiire:
        ft_issues.append({"row": i, "name": name, "status": status, "tanka": tanka, "shiire": shiire})

result["FT_issues"] = ft_issues

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\missing_prices.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("TERRA 単価空欄:", len(terra_issues), "件")
for x in terra_issues:
    print(f"  行{x['row']}: {x['name']} {x['kubun']} tanka={x['tanka']} shiire={x['shiire']}")
print("FT 単価空欄:", len(ft_issues), "件")
for x in ft_issues:
    print(f"  行{x['row']}: {x['name']} tanka={x['tanka']} shiire={x['shiire']}")
