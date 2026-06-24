import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()

# mail_pipeline の実体を探す
print("■ mail_pipeline 実体探索")
# ディレクトリ
mp_dir = os.path.join(SES, "mail_pipeline")
if os.path.isdir(mp_dir):
    print("  mail_pipeline/ ディレクトリ存在")
    for fn in os.listdir(mp_dir):
        fp = os.path.join(mp_dir, fn)
        sz = os.path.getsize(fp) if os.path.isfile(fp) else "-"
        print(f"    {fn} ({sz}b)")
else:
    print("  mail_pipeline/ ディレクトリなし")

# ses_work直下のpyファイル
print("\n■ ses_work直下の主要ファイル")
for fn in sorted(os.listdir(SES)):
    if fn.endswith((".py", ".bat", ".json", ".md", ".txt")) and not fn.startswith("_jobz"):
        fp = os.path.join(SES, fn)
        if os.path.isfile(fp):
            sz = os.path.getsize(fp)
            print(f"  {fn} ({sz}b)")

# run_pipeline.bat 確認
print("\n■ mail_pipeline/run_pipeline.bat 内容")
rpb = os.path.join(SES, "mail_pipeline", "run_pipeline.bat")
if os.path.exists(rpb):
    with open(rpb, encoding="cp932", errors="replace") as f:
        print(f.read())
else:
    print("  未存在")

# mail_pipeline内の主要Pythonファイル確認
print("\n■ mail_pipeline内の主要Pythonファイル")
for fn in ["main.py", "pipeline.py", "mail_pipeline.py", "fetcher.py"]:
    fp = os.path.join(SES, "mail_pipeline", fn)
    if os.path.exists(fp):
        with open(fp, encoding="utf-8", errors="replace") as f:
            content = f.read()
        print(f"\n  --- {fn} 冒頭100行 ---")
        for i, line in enumerate(content.split("\n")[:100], 1):
            print(f"  L{i}: {line}")

# wd_mail_pipeline.bat 内容再確認
print("\n■ wd_mail_pipeline.bat 内容")
wmp = os.path.join(SES, "wd_mail_pipeline.bat")
if os.path.exists(wmp):
    with open(wmp, encoding="cp932", errors="replace") as f:
        print(f.read())
