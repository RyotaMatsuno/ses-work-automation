import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log_file = "task_auto_runner/logs/bootstrap_run.log"
err_file = "task_auto_runner/logs/bootstrap_err.log"

# 進捗確認: ログサイズと最近の生成ファイル
print("=== Bootstrap Run Log Size ===")
if os.path.exists(log_file):
    print(f"size: {os.path.getsize(log_file)} bytes")
    print(f"mtime: {time.ctime(os.path.getmtime(log_file))}")
else:
    print("(not yet)")

print("\n=== Err Log Tail ===")
if os.path.exists(err_file):
    with open(err_file, encoding="utf-8", errors="replace") as f:
        content = f.read()
    print(content[-2000:] if content else "(empty)")
else:
    print("(not yet)")

print("\n=== task_auto_runner/ contents ===")
for f in sorted(os.listdir("task_auto_runner")):
    p = os.path.join("task_auto_runner", f)
    if os.path.isfile(p):
        print(f"  {f}: {os.path.getsize(p)} bytes")
    elif os.path.isdir(p):
        print(f"  {f}/ (dir)")

print("\n=== Process Check ===")
import subprocess

result = subprocess.run(["tasklist", "/fi", "imagename eq node.exe"], capture_output=True, text=True)
print(result.stdout[-2000:])
