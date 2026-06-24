import subprocess

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\invoice_auto.log"
with open(log_path, "a", encoding="utf-8") as logf:
    proc = subprocess.Popen(
        ["python", "freee_invoice_v2.py"],
        cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee",
        stdout=logf,
        stderr=logf,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
print(f"freee PID: {proc.pid}")
