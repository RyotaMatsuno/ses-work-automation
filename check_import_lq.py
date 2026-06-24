# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# import確認
r = subprocess.run(
    [
        sys.executable,
        "-c",
        "import sys; sys.path.insert(0, r'C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work\\line_webhook'); "
        "from line_query import handle_line_query; print('import OK')",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook",
    timeout=15,
)
print(r.stdout.strip())
if r.stderr:
    print("ERR:", r.stderr[:300])
