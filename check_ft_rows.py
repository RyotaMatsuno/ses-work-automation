# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
import openpyxl

XLSX_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\契約マスター_v6.xlsx"
wb = openpyxl.load_workbook(XLSX_PATH)
ws_ft = wb["フラップテック"]

# 空き行を探す（14/15行目を確認）
for chk in [14, 15, 17, 18, 19, 20]:
    v = ws_ft.cell(row=chk, column=2).value
    print(f"行{chk} col2: {v}", flush=True)
