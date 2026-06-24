import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

out_lines = []

# tasklist で全プロセス確認
r = subprocess.run("tasklist /fo csv", shell=True, capture_output=True)
lines = r.stdout.decode("cp932", errors="replace").splitlines()
codex_lines = [l for l in lines if "codex" in l.lower() or "node" in l.lower()]
out_lines.append("=== node/codex processes ===")
out_lines.extend(codex_lines[:20])

# matching_v3内の最近変更されたファイル
base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3"
now = time.time()
out_lines.append("\n=== Recently modified files in matching_v3 (last 10min) ===")
for root, dirs, files in os.walk(base):
    for fname in files:
        fpath = os.path.join(root, fname)
        try:
            mtime = os.path.getmtime(fpath)
            if now - mtime < 600:
                rel = fpath.replace(base, "").replace("\\", "/")
                out_lines.append(f"  {rel} ({int(now - mtime)}s ago)")
        except:
            pass

# logファイルサイズ
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_phase_e.log"
size = os.path.getsize(log) if os.path.exists(log) else -1
out_lines.append(f"\n=== codex_phase_e.log: {size} bytes ===")

print("\n".join(out_lines))
