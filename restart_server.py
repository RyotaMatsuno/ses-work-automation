import subprocess, os, time

# 既存の8765プロセスをkill
result = subprocess.run(
    'netstat -ano | findstr ":8765 " | findstr "LISTENING"',
    shell=True, capture_output=True, text=True
)
for line in result.stdout.strip().splitlines():
    parts = line.split()
    if parts:
        pid = parts[-1]
        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
        print(f"killed PID {pid}")

time.sleep(2)

# 新しいサーバーをバックグラウンド起動
proc = subprocess.Popen(
    ["pythonw", "command_server.py"],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\local_server",
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
)
print(f"サーバー起動 PID: {proc.pid}")
time.sleep(3)
print("完了")
