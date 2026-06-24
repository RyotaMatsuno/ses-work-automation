p = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer\importer.py"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

# Content-Dispositionのstr変換が必要な箇所を確認
if "Content-Disposition" in c:
    idx = c.find("Content-Disposition")
    print("Found at:", idx)
    print(repr(c[max(0, idx - 40) : idx + 100]))
else:
    print("Not found in importer.py")

# 未処理UIDの件数確認
import json
import os

processed_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer\processed_ids.json"
if os.path.exists(processed_path):
    with open(processed_path) as f:
        ids = json.load(f)
    print(f"processed_ids: {len(ids)}件")
else:
    print("processed_ids.json: なし（初回）")
