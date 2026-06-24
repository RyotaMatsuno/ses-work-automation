import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
cwd = os.path.join(
    os.path.expanduser("~"), "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work", "flag_auto_updater"
)
result = subprocess.run(
    [sys.executable, "estimate_engineer_attrs.py"],
    cwd=cwd,
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    timeout=1200,
)
out = result.stdout + result.stderr
print(out[-4000:] if len(out) > 4000 else out)
print("returncode:", result.returncode)
