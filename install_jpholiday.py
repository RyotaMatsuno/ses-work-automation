import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
r = subprocess.run("pip install jpholiday --quiet --break-system-packages", shell=True, capture_output=True)
print(r.stdout.decode("utf-8", errors="replace").strip()[:200] or "install ok")
print(r.stderr.decode("utf-8", errors="replace").strip()[:200])
# 動作確認
import importlib.util

spec = importlib.util.find_spec("jpholiday")
print("jpholiday:", "OK" if spec else "NOT FOUND")
