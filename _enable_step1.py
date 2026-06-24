import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

tasks = ["SES_MatchingV3", "jobz_importer"]
for t in tasks:
    result = subprocess.run(
        ["schtasks", "/change", "/tn", t, "/enable"], capture_output=True, encoding="cp932", errors="replace"
    )
    if result.returncode == 0:
        print(f"✅ {t}: 有効化完了")
    else:
        print(f"❌ {t}: {result.stdout.strip()} {result.stderr.strip()}")

# 確認
print("\n=== 有効化後の状態確認 ===")
for t in tasks:
    result = subprocess.run(
        ["schtasks", "/query", "/tn", t, "/fo", "LIST"], capture_output=True, encoding="cp932", errors="replace"
    )
    for line in result.stdout.split("\n"):
        if "状態" in line or "次回" in line:
            print(f"  {t}: {line.strip()}")
