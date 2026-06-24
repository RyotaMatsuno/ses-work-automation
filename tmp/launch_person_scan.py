# -*- coding: utf-8 -*-
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

cwd = os.path.dirname(os.path.abspath(__file__))
script = os.path.join(cwd, "scan_person_only.py")
log_path = os.path.join(cwd, "scan_person_log.txt")

proc = subprocess.Popen(
    ["python", "-u", script],
    cwd=cwd,
    stdout=open(log_path, "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    creationflags=0x00000008,
)
print(f"PID: {proc.pid}")
print(f"ログ: {log_path}")
