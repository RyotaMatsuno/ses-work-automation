import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# matching_v3の本日13:00実行ログを確認
print("=== matching_v3 本日ログ ===")
log_dir = base / "matching_v3" / "logs"
from datetime import date

today = str(date.today()).replace("-", "")
today_log = log_dir / f"matching_v3_{today}.log"
if today_log.exists():
    lines = today_log.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"  {today_log.name} ({len(lines)}行)")
    for l in lines[-30:]:
        print(f"  {l}")
else:
    print(f"  {today_log.name} 未生成（13:00タスクが未実行または失敗）")
    # 最新ログを確認
    logs = sorted(log_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
    if logs:
        print(f"  最新: {logs[0].name} mtime={logs[0].stat().st_mtime}")

# mail_pipeline本日ログ確認
print("\n=== mail_pipeline 本日ログ ===")
mp_log_dirs = [base / "mail_pipeline" / "logs", base / "logs"]
for ld in mp_log_dirs:
    if ld.exists():
        logs = sorted(ld.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        for l in logs[:3]:
            mtime_str = str(l.stat().st_mtime)
            lines = l.read_text(encoding="utf-8", errors="replace").splitlines()
            today_lines = [ll for ll in lines if "2026-06-05" in ll or "2026/06/05" in ll]
            if today_lines:
                print(f"  {l.name} - 本日分{len(today_lines)}行:")
                for ll in today_lines[-10:]:
                    print(f"    {ll}")
        break

# LINE月次カウントを確認
print("\n=== LINE通知ログ（直近） ===")
for log_name in ["notify_line.log", "line_notify.log", "matching_v3/logs/notify.log"]:
    lp = base / log_name
    if lp.exists():
        lines = lp.read_text(encoding="utf-8", errors="replace").splitlines()
        print(f"  {log_name}: {len(lines)}行")
        for l in lines[-10:]:
            print(f"    {l}")
        break
