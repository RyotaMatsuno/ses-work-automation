import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

SES = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
IMP = os.path.join(SES, "mail_attachment_importer")

results = {}

# --- 1. ライブラリインストール確認 ---
libs = ["openpyxl", "pdfplumber", "docx", "anthropic", "playwright"]
for lib in libs:
    r = subprocess.run(
        [sys.executable, "-c", f'import {lib}; print({lib}.__version__ if hasattr({lib},"__version__") else "ok")'],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=SES,
    )
    results[f"lib/{lib}"] = r.stdout.strip() if r.returncode == 0 else f"NG: {r.stderr.strip()[:60]}"

# --- 2. 各モジュールimport確認 ---
modules = ["mail_fetcher", "file_parser", "ai_extractor", "notion_writer", "sheet_fetcher", "importer"]
for mod in modules:
    r = subprocess.run(
        [sys.executable, "-c", f'import sys; sys.path.insert(0,r"{IMP}"); import {mod}; print("OK")'],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=IMP,
    )
    results[f"import/{mod}"] = r.stdout.strip() if r.returncode == 0 else f"NG: {r.stderr.strip()[-120:]}"

# --- 3. file_parser対応形式確認 ---
r = subprocess.run(
    [
        sys.executable,
        "-c",
        f'import sys; sys.path.insert(0,r"{IMP}"); from file_parser import parse_file; '
        f'print(parse_file.__doc__ or "no doc"); '
        f"import inspect; src=inspect.getsource(parse_file); "
        f'print("xlsx:", "xlsx" in src or "openpyxl" in src); '
        f'print("pdf:", "pdf" in src or "pdfplumber" in src); '
        f'print("docx:", "docx" in src); '
        f'print("pptx:", "pptx" in src or "pptx" in src.lower()); '
        f'print("csv:", "csv" in src)',
    ],
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    cwd=IMP,
)
results["file_parser/対応形式"] = r.stdout.strip() if r.returncode == 0 else f"NG: {r.stderr[-120:]}"

# --- 4. ai_extractor classify_content動作確認 ---
r2 = subprocess.run(
    [
        sys.executable,
        "-c",
        f'import sys; sys.path.insert(0,r"{IMP}"); from ai_extractor import classify_content; '
        f'r1=classify_content("氏名: 山田太郎 スキル: Java"); '
        f'r2=classify_content("必須スキル: Java 勤務地: 東京 期間: 6ヶ月"); '
        f'print("人員:", r1, " 案件:", r2)',
    ],
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    cwd=IMP,
)
results["ai_extractor/classify_content"] = r2.stdout.strip() if r2.returncode == 0 else f"NG: {r2.stderr[-120:]}"

# --- 5. file_parserのpptx・csv対応確認（ソース直読み） ---
fp_path = os.path.join(IMP, "file_parser.py")
with open(fp_path, encoding="utf-8") as f:
    fp_src = f.read()
results["file_parser/xlsx"] = "OK" if ("openpyxl" in fp_src or "xlsx" in fp_src) else "NG"
results["file_parser/pdf"] = "OK" if "pdfplumber" in fp_src else "NG"
results["file_parser/docx"] = "OK" if "python-docx" in fp_src or "docx" in fp_src else "NG"
results["file_parser/pptx"] = "OK" if "pptx" in fp_src.lower() else "未対応"
results["file_parser/csv"] = "OK" if "csv" in fp_src else "未対応"
results["file_parser/xls(旧)"] = "OK" if "xlrd" in fp_src or ".xls" in fp_src else "要確認"

# --- 6. タスクスケジューラ登録確認 ---
r3 = subprocess.run(
    ["schtasks", "/query", "/TN", "jobz_importer", "/FO", "LIST"],
    capture_output=True,
    encoding="utf-8",
    errors="replace",
)
results["scheduler/jobz_importer"] = "OK" if r3.returncode == 0 else "NG（未登録）"

print("=" * 60)
print("mail_attachment_importer チェック結果")
print("=" * 60)
for k, v in results.items():
    icon = (
        "✅"
        if str(v).startswith("OK") or str(v) == "ok" or str(v).startswith("0.") or str(v).startswith("1.")
        else ("❌" if "NG" in str(v) else "⚠️")
    )
    print(f"  {icon} {k}: {v}")
