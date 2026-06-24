# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# /change では効かないので /delete → /create で再登録
r1 = subprocess.run(["schtasks", "/delete", "/tn", "SES_MatchingV3", "/f"], capture_output=True, timeout=10)
print("削除:", r1.stdout.decode("cp932", errors="replace").strip())

r2 = subprocess.run(
    [
        "schtasks",
        "/create",
        "/tn",
        "SES_MatchingV3",
        "/tr",
        r'cmd.exe /c "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\wd_matching_v3.bat"',
        "/sc",
        "DAILY",
        "/st",
        "08:00",
        "/ru",
        "ma_py",
        "/f",
    ],
    capture_output=True,
    timeout=10,
)
print("登録:", r2.stdout.decode("cp932", errors="replace").strip())

# 確認
r3 = subprocess.run(["schtasks", "/query", "/tn", "SES_MatchingV3", "/fo", "LIST"], capture_output=True, timeout=10)
out = r3.stdout.decode("cp932", errors="replace")
for line in out.splitlines():
    if any(k in line for k in ["次回", "スケジュール", "実行するタスク"]):
        print(line.strip())
