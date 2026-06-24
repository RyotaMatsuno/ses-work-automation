import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\flag_auto_updater",
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
print(result.stderr[-1000:] if result.stderr else "")
print("returncode:", result.returncode)
