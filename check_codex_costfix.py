import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\codex_costfix.log")
result = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\check_costfix_result.txt")

print(f"ログサイズ: {log.stat().st_size if log.exists() else 'なし'} bytes")
if log.exists():
    with open(log, encoding="utf-8", errors="replace") as f:
        content = f.read()
    print(f"末尾500文字:\n{content[-500:]}")

print(f"\nresult存在: {result.exists()}")
if result.exists():
    with open(result, encoding="utf-8", errors="replace") as f:
        print(f.read())
