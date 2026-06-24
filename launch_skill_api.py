import os
import subprocess
import time

ses_work = os.path.expandvars(r"%USERPROFILE%\OneDrive\デスクトップ\ses_work")
py = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Python\Python312\pythonw.exe")

proc = subprocess.Popen(
    [py, r"skill_reader\skill_reader_api.py"],
    cwd=ses_work,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
)
print(f"起動: PID={proc.pid}")
time.sleep(3)
print("3秒待機完了")
