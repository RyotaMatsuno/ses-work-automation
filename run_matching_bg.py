import subprocess, sys
proc = subprocess.Popen(
    [sys.executable, "matching_v2/matching_v2.py"],
    stdout=open("matching_v2_run.log", "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    creationflags=0x00000008  # DETACHED_PROCESS
)
print(f"PID: {proc.pid}")
