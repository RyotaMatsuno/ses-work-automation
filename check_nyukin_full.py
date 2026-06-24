# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
import openpyxl

XLSX_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\契約マスター_v6.xlsx"
wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
ws = wb["入金予測"]

print("=== 入金予測 全行（空行除く）===", flush=True)
headers = None
for i, row in enumerate(ws.iter_rows(min_row=1, values_only=True), start=1):
    if i == 3:
        headers = row[:12]
        print(f"行{i}[HEADER]: {headers}", flush=True)
        continue
    if any(v is not None for v in row[:12]):
        print(f"行{i}: {row[:12]}", flush=True)
