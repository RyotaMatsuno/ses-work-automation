import os

# matching_v3配下のファイル一覧
base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3"
for root, dirs, files in os.walk(base):
    # logsは除外
    dirs[:] = [d for d in dirs if d not in ("logs", "__pycache__", ".git")]
    level = root.replace(base, "").count(os.sep)
    indent = "  " * level
    print(f"{indent}{os.path.basename(root)}/")
    for f in files:
        fpath = os.path.join(root, f)
        size = os.path.getsize(fpath)
        print(f"{indent}  {f}  ({size:,} bytes)")
