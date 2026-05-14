import subprocess, sys, os

work_dir = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
log_path = os.path.join(work_dir, "cleanup_v2_new.log")
script   = os.path.join(work_dir, "cleanup_v2.py")

with open(log_path, "w", encoding="utf-8") as log_f:
    proc = subprocess.Popen(
        [sys.executable, script],
        cwd=work_dir,
        stdout=log_f,
        stderr=log_f,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

print(f"PID: {proc.pid}")
