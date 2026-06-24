import os
import socket
import subprocess
import time

# 既存8080をkill
os.system("for /f \"tokens=5\" %a in ('netstat -ano ^| findstr :8080') do taskkill /PID %a /F 2>nul")
time.sleep(1)

# callback_server起動
proc = subprocess.Popen(
    ["python", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\callback_server.py"],
    creationflags=subprocess.CREATE_NEW_CONSOLE,
)
time.sleep(2)

# 確認
s = socket.socket()
s.settimeout(2)
try:
    s.connect(("localhost", 8080))
    print(f"OK: PID={proc.pid} localhost:8080起動済み")
except:
    print("NG: 起動失敗")
finally:
    s.close()
