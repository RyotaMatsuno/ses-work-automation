import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
r = subprocess.run('schtasks /query /fo csv 2>nul | findstr /i "freee"', shell=True, capture_output=True)
for line in r.stdout.decode("utf-8", errors="replace").strip().split("\n"):
    if line.strip():
        parts = line.strip('"').split('","')
        name = parts[0] if parts else ""
        next_run = parts[1] if len(parts) > 1 else ""
        status = parts[2] if len(parts) > 2 else ""
        print(f"  {name:<35} 次回:{next_run}  状態:{status}")
