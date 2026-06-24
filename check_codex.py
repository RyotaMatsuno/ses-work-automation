import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

out_lines = []

# 子プロセス確認
r = subprocess.run(
    ["wmic", "process", "where", "ParentProcessId=25684", "get", "ProcessId,Name,CommandLine"], capture_output=True
)
out_lines.append("=== Child processes of 25684 ===")
out_lines.append(r.stdout.decode("cp932", errors="replace").strip())

# matching_v3内の最近変更されたファイル
import time

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3"
now = time.time()
out_lines.append("\n=== Recently modified files in matching_v3 (last 10min) ===")
for root, dirs, files in os.walk(base):
    for fname in files:
        fpath = os.path.join(root, fname)
        try:
            mtime = os.path.getmtime(fpath)
            if now - mtime < 600:
                rel = fpath.replace(base, "")
                out_lines.append(f"  {rel} ({int(now - mtime)}s ago)")
        except:
            pass

# logファイルサイズ
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_phase_e.log"
size = os.path.getsize(log) if os.path.exists(log) else -1
out_lines.append(f"\n=== codex_phase_e.log size: {size} bytes ===")

result = "\n".join(out_lines)
print(result)
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_check.txt", "w", encoding="utf-8") as f:
    f.write(result)
