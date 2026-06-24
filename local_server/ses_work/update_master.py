import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SA_FILE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json"

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(SA_FILE, scopes=scopes)
gc = gspread.authorize(creds)
sh = gc.open_by_key(SPREADSHEET_ID)

terra = sh.worksheet("TERRA")
all_vals = terra.get_all_values()

# ① 加藤(T) → ステータスを「退場済み」に変更（行26、ステータスはC列=index2）
for i, row in enumerate(all_vals):
    for cell in row:
        if "加藤" in str(cell) and i > 0:
            # ステータス列(C列=3列目)を確認
            print(f"加藤(T) 行{i + 1}: ステータス現在値='{row[2]}', 期間列='{row[5]}'")
            # ステータスをC列(col=3)→「退場済み」
            terra.update_cell(i + 1, 3, "退場済み")
            # 期間列(F列=6)→「退場済み」
            terra.update_cell(i + 1, 6, "退場済み")
            print(f"→ 行{i + 1} 加藤(T) ステータス・期間を「退場済み」に更新完了")
            break

# ② 片山 → 期間を「7月末終了」に変更（TERRAシート行12）
for i, row in enumerate(all_vals):
    for cell in row:
        if "片山" in str(cell) and i > 0:
            print(f"\n片山 行{i + 1}: ステータス現在値='{row[2]}', 期間列='{row[5]}'")
            # ステータス列(C列=3)→「稼働中」
            terra.update_cell(i + 1, 3, "稼働中")
            # 期間列(F列=6)→「7月末終了」
            terra.update_cell(i + 1, 6, "7月末終了")
            print(f"→ 行{i + 1} 片山 ステータス「稼働中」・期間「7月末終了」に更新完了")
            break

print("\n全更新完了")
