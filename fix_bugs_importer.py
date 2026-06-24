import sys

sys.stdout.reconfigure(encoding="utf-8")

IMP = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer"

# ===== バグ① mail_fetcher.py SUPPORTED_EXTS =====
mf_path = IMP + r"\mail_fetcher.py"
with open(mf_path, encoding="utf-8") as f:
    mf = f.read()

old_exts = 'SUPPORTED_EXTS = {".xlsx", ".xls", ".pdf", ".docx", ".doc"}'
new_exts = 'SUPPORTED_EXTS = {".xlsx", ".xls", ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".csv", ".tsv"}'

if old_exts in mf:
    mf = mf.replace(old_exts, new_exts, 1)
    with open(mf_path, "w", encoding="utf-8") as f:
        f.write(mf)
    print("バグ①修正OK: SUPPORTED_EXTS にpptx/ppt/csv/tsv追加")
elif new_exts in mf:
    print("バグ①: 既に修正済み")
else:
    print("バグ①: 対象行が見つかりません（手動確認要）")

# ===== バグ③ importer.py テキスト長200→50 =====
imp_path = IMP + r"\importer.py"
with open(imp_path, encoding="utf-8") as f:
    imp = f.read()

old_len = "if not text or len(text.strip()) < 200:"
new_len = "if not text or len(text.strip()) < 50:"

if old_len in imp:
    imp = imp.replace(old_len, new_len, 1)
    with open(imp_path, "w", encoding="utf-8") as f:
        f.write(imp)
    print("バグ③修正OK: テキスト長チェック 200→50文字")
elif new_len in imp:
    print("バグ③: 既に50文字になっている")
else:
    print("バグ③: 対象行が見つかりません")
