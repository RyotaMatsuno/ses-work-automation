
import openpyxl, json

# 最初のバックアップで川崎・齋藤を確認
BAK = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\契約マスター_v6_bak_20260521_023136.xlsx"
wb = openpyxl.load_workbook(BAK, data_only=True)
ws = wb["TERRA"]

result = []
for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
    if i < 5: continue
    if not row[3]: continue
    name = str(row[3]).strip()
    status = str(row[2] or "").strip()
    tanka = row[7]
    shiire = row[13]
    result.append({"row": i, "name": name, "status": status, "tanka": tanka, "shiire": shiire,
                   "kubun": str(row[1] or ""), "tantou": str(row[0] or ""), "case": str(row[6] or "")})

# 全員を出力して確認
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\bak_terra.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("done:", len(result))
