import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
python = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"
mv3 = os.path.join(SES, "matching_v3")

print("■ matching_v3 手動実行（本番）")
r = subprocess.run(
    [python, "matching_v3.py"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=mv3, timeout=120
)
print(f"  returncode: {r.returncode}")
print("\n  stdout:")
print(r.stdout[:3000])
if r.stderr:
    print(f"\n  stderr: {r.stderr[:500]}")
