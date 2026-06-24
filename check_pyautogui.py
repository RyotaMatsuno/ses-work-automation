# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# pyautogui インストール確認
r = subprocess.run(
    [sys.executable, "-c", "import pyautogui; print('OK', pyautogui.__version__)"],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
print("pyautogui:", r.stdout.strip() or r.stderr.strip())

# Cursorウィンドウが見えるか確認
r2 = subprocess.run(
    [
        "powershell",
        "-Command",
        "Get-Process | Where-Object {$_.MainWindowTitle -like '*Cursor*' -or $_.Name -like '*Cursor*'} | Select-Object Name, MainWindowTitle | Format-List",
    ],
    capture_output=True,
    text=True,
    encoding="cp932",
    errors="replace",
)
print("Cursorプロセス:", r2.stdout.strip() or "見つからない")
