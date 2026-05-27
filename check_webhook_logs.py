import sys, io, os, glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Webhookサーバーのログを探す
base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
log_files = glob.glob(os.path.join(base, "*.log")) + glob.glob(os.path.join(base, "**", "*.log"), recursive=True)
print("ログファイル一覧:")
for f in log_files:
    size = os.path.getsize(f)
    mtime = os.path.getmtime(f)
    print(f"  {f} ({size}bytes)")

print()

# line_webhook ディレクトリ構成
for root, dirs, files in os.walk(base):
    level = root.replace(base, '').count(os.sep)
    indent = ' ' * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = ' ' * 2 * (level + 1)
    for f in files:
        fpath = os.path.join(root, f)
        size = os.path.getsize(fpath)
        print(f"{subindent}{f} ({size}bytes)")
