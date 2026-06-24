import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 現在登録済みタスク確認
r = subprocess.run('schtasks /query /fo csv 2>nul | findstr /i "freee"', shell=True, capture_output=True)
print(r.stdout.decode("utf-8", errors="replace"))

# Pythonパス確認
r2 = subprocess.run("where python", shell=True, capture_output=True)
print("python path:", r2.stdout.decode("utf-8", errors="replace").strip().split("\n")[0])
