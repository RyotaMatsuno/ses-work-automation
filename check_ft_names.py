# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
import openpyxl

XLSX_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\契約マスター_v6.xlsx"
wb = openpyxl.load_workbook(XLSX_PATH)
ws_ft = wb["フラップテック"]

# FT全行の氏名確認
print("FT全行氏名:", flush=True)
for i, row in enumerate(ws_ft.iter_rows(min_row=4, values_only=True), start=4):
    if row[2]:
        print(f"  行{i}: {row[2]}", flush=True)
