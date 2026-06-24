import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
cwd = os.path.join(
    os.path.expanduser("~"), "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work", "flag_auto_updater"
)
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
    cwd=cwd,
    capture_output=True,
    encoding="utf-8",
    errors="replace",
)
out = result.stdout + result.stderr
print(out[-3000:] if len(out) > 3000 else out)
print("returncode:", result.returncode)
