# -*- coding: utf-8 -*-
import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# タスク一覧をCSVで取得して内容確認
result = subprocess.run("schtasks /query /fo CSV", shell=True, capture_output=True, encoding="cp932", errors="replace")
for line in result.stdout.splitlines():
    # mail,pipeline,ses,outlook含む行を表示
    low = line.lower()
    if any(k in low for k in ["mail", "pipeline", "ses", "outlook", "matching"]):
        print(line)
print("---全タスク名---")
for line in result.stdout.splitlines()[1:]:
    cols = line.strip('"').split('","')
    if cols:
        print(cols[0])
