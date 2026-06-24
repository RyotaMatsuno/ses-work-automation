import os
import subprocess

log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\codex_run.log"
out_file = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\diag.txt"

lines = []
lines.append(f"log size: {os.path.getsize(log)}")

r1 = subprocess.run('tasklist /FI "PID eq 6028"', shell=True, capture_output=True, text=True, encoding="cp932")
lines.append("PID 6028: " + r1.stdout.strip())

r2 = subprocess.run(
    'tasklist /FI "IMAGENAME eq node.exe"', shell=True, capture_output=True, text=True, encoding="cp932"
)
lines.append("node procs:\n" + r2.stdout.strip())

with open(out_file, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("diag written", flush=True)
