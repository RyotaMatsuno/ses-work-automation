import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

tasks = [
    "SES_MailPipeline",
    "SES_MatchingV3",
    "jobz_importer",
    "line_bridge_worker_health",
    "usage_tracker_daily",
    "SES_TaskAutoRunner",
]

print("=== 全タスク状態（再稼働後） ===")
for t in tasks:
    result = subprocess.run(
        ["schtasks", "/query", "/tn", t, "/fo", "LIST"], capture_output=True, encoding="cp932", errors="replace"
    )
    if result.returncode == 0:
        lines = result.stdout.split("\n")
        status = next((l.strip() for l in lines if "状態" in l), "?")
        nextrun = next((l.strip() for l in lines if "次回" in l), "")
        print(f"  {'✅' if '準備完了' in status else '❌'} {t}")
        print(f"    {status}")
        if nextrun:
            print(f"    {nextrun}")
    else:
        print(f"  ❓ {t}: 未登録")
