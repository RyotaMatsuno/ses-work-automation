import subprocess
import sys

fpath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
result = subprocess.run(
    ["python", "-m", "py_compile", fpath], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
sys.stdout.buffer.write(f"Syntax: {'OK' if result.returncode == 0 else result.stderr}\n".encode())
