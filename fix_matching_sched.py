# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# SES_MatchingV3を08:00の1回実行に修正
r = subprocess.run(
    ["schtasks", "/change", "/tn", "SES_MatchingV3", "/sc", "DAILY", "/st", "08:00"], capture_output=True, timeout=10
)
print("スケジュール修正:", r.stdout.decode("cp932", errors="replace").strip())

# 確認
r2 = subprocess.run(["schtasks", "/query", "/tn", "SES_MatchingV3", "/fo", "LIST"], capture_output=True, timeout=10)
out = r2.stdout.decode("cp932", errors="replace")
for line in out.splitlines():
    if any(k in line for k in ["次回", "前回", "スケジュール", "状態"]):
        print(line.strip())
