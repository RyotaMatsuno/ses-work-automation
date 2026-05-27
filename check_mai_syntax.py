
import os, sys

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
sys.path.insert(0, os.path.join(base, "mail_attachment_importer"))

# ai_extractor と notion_writer の単体テスト（API呼び出しなし部分）
ai_path = os.path.join(base, "mail_attachment_importer", "ai_extractor.py")
nw_path = os.path.join(base, "mail_attachment_importer", "notion_writer.py")
sf_path = os.path.join(base, "mail_attachment_importer", "sheet_fetcher.py")

for p in [ai_path, nw_path, sf_path]:
    fname = os.path.basename(p)
    if os.path.exists(p):
        import py_compile
        try:
            py_compile.compile(p, doraise=True)
            print(f"SYNTAX OK: {fname}")
        except py_compile.PyCompileError as e:
            print(f"SYNTAX NG: {fname} - {e}")
    else:
        print(f"NOT FOUND: {fname}")
