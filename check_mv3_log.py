import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
log_dir = base / "matching_v3" / "logs"
today = str(date.today()).replace("-", "")
log = log_dir / f"matching_v3_{today}.log"

print(f"=== {log.name} ===")
if log.exists():
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"{len(lines)}行")
    for l in lines[-20:]:
        print(f"  {l}")
else:
    print("  未生成")
    # 直近ログ
    logs = sorted(log_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
    if logs:
        latest = logs[0]
        lines = latest.read_text(encoding="utf-8", errors="replace").splitlines()
        print(f"  最新: {latest.name} ({len(lines)}行)")
        for l in lines[-10:]:
            print(f"  {l}")
