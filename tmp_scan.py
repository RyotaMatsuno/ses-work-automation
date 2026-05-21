
import openpyxl
EXCEL_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\契約マスター_v6.xlsx"
SHEET_CONFIGS = {
    "TERRA":         {"name_col": 4, "status_col": 3, "start_row": 5},
    "フラップテック": {"name_col": 3, "status_col": 2, "start_row": 4},
    "グレイスライン": {"name_col": 2, "status_col": 1, "start_row": 4},
}
wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
found = False
for sheet_name, cfg in SHEET_CONFIGS.items():
    ws = wb[sheet_name]
    nc, sc = cfg["name_col"]-1, cfg["status_col"]-1
    for row in ws.iter_rows(min_row=cfg["start_row"], values_only=True):
        status = str(row[sc] or "").strip()
        if status == "入場前":
            print(f"HIT: {sheet_name} | {row[nc]}")
            found = True
if not found:
    print("入場前: 0名（現在なし）")
print("scan完了")
