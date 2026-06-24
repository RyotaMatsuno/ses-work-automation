import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

# プロセス確認
result = subprocess.run(
    ["tasklist", "/fi", "imagename eq python.exe", "/fo", "csv"], capture_output=True, text=True, encoding="cp932"
)
print("Pythonプロセス一覧:")
print(result.stdout)
