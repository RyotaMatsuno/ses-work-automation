import subprocess

proc = subprocess.Popen(
    ["pip", "install", "sentence-transformers", "--break-system-packages", "-q"],
    stdout=open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pip_install.log", "w"),
    stderr=subprocess.STDOUT,
    creationflags=0x00000008,  # DETACHED_PROCESS
)
print(f"PID: {proc.pid} - installing sentence-transformers in background")
