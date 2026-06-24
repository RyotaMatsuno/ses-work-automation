# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

r = subprocess.run(
    [sys.executable, "-m", "pip", "install", "pyautogui", "pygetwindow", "--break-system-packages", "-q"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print(r.stdout[-300:] if r.stdout else "")
print(r.stderr[-300:] if r.stderr else "")

r2 = subprocess.run(
    [sys.executable, "-c", "import pyautogui, pygetwindow; print('OK')"],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
print("確認:", r2.stdout.strip() or r2.stderr.strip())
