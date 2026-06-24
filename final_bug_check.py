import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

IMP = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer"

results = {}

# 構文チェック
for f in ["mail_fetcher.py", "file_parser.py", "importer.py", "ai_extractor.py", "notion_writer.py"]:
    r = subprocess.run([sys.executable, "-m", "py_compile", f], capture_output=True, cwd=IMP)
    results[f"構文/{f}"] = "OK" if r.returncode == 0 else "NG"

# SUPPORTED_EXTS確認
with open(IMP + r"\mail_fetcher.py", encoding="utf-8") as f:
    mf = f.read()
for ext in [".xlsx", ".pdf", ".docx", ".pptx", ".ppt", ".csv", ".tsv"]:
    results[f"SUPPORTED_EXTS/{ext}"] = "OK" if f'"{ext}"' in mf else "NG"

# okamotoアカウント
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
results[".env/OKAMOTO_EMAIL"] = "OK" if cfg.get("OKAMOTO_EMAIL") else "NG"
results[".env/OKAMOTO_PASSWORD"] = "OK" if cfg.get("OKAMOTO_PASSWORD") else "NG"

# テキスト長チェック
with open(IMP + r"\importer.py", encoding="utf-8") as f:
    imp = f.read()
results["テキスト長チェック(<50)"] = "OK" if "< 50" in imp and "< 200" not in imp else "NG"

print("=" * 55)
print("最終バグ修正チェック結果")
print("=" * 55)
all_ok = True
for k, v in results.items():
    icon = "✅" if v == "OK" else "❌"
    if v != "OK":
        all_ok = False
    print(f"  {icon} {k}: {v}")
print("=" * 55)
print(f"  {'✅ 全項目クリア。運用開始OK' if all_ok else '❌ 要修正項目あり'}")
