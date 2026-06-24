import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
    cwd=r"C:\Users\ma_py\OneDrive\u30c7\u30b9\u30af\u30c8\u30c3\u30d7\ses_work\flag_auto_updater".encode().decode(
        "unicode_escape"
    ),
    capture_output=True,
    encoding="utf-8",
    errors="replace",
)
print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-500:])
print("returncode:", result.returncode)
