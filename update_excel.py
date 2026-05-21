
import openpyxl
from datetime import datetime
import shutil

EXCEL_PATH = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\契約マスター_v6.xlsx'
BAK_PATH = f'C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work\\contract\\契約マスター_v6_bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

shutil.copy2(EXCEL_PATH, BAK_PATH)
print(f"バックアップ: {BAK_PATH}")

wb = openpyxl.load_workbook(EXCEL_PATH)
changes = []

# --- 修正①: FTシート 原昌志 → 5月末終了 ---
ws_ft = wb['フラップテック']
for row in ws_ft.iter_rows(min_row=4):
    name = row[2].value  # C列: 氏名
    status = row[1].value  # B列: ステータス
    if name == '原昌志' and status == '稼働中':
        row[1].value = '5月末終了'
        row[4].value = '5月末終了'  # E列: 期間
        changes.append(f"FT: 原昌志 ステータス→5月末終了, 期間→5月末終了")
        break

wb.save(EXCEL_PATH)
print("変更内容:")
for c in changes:
    print(f"  {c}")
print("保存完了")
