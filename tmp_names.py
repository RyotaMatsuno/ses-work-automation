
import openpyxl, json

EXCEL_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\契約マスター_v6.xlsx"
wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)

out = {}
for sname in ["TERRA", "フラップテック"]:
    ws = wb[sname]
    names = []
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        # 氏名列
        nc = 3 if sname == "TERRA" else 2  # 0-indexed
        status_col = 2 if sname == "TERRA" else 1
        if i >= 5:
            n = row[nc]
            s = row[status_col]
            if n:
                names.append({"row": i, "name": str(n), "status": str(s)})
    out[sname] = names

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\names.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("done")
