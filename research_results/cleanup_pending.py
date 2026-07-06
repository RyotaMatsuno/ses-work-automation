import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os
import shutil

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"
DONE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\done_tasks"

stale = [
    "00_ORCHESTRATION_R5_accuracy__try2.md",
    "05_20260625_143203_batch_backfill__try2.md",
    "06_20260625_143203_matching_hardfilter__try1.md",
]

for f in stale:
    src = os.path.join(PENDING, f)
    dst = os.path.join(DONE, f)
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"Moved to done: {f}")
    else:
        print(f"Not found: {f}")

remaining = [f for f in os.listdir(PENDING) if not f.startswith('.') and not f.startswith('_')]
print(f"\nPending tasks remaining: {len(remaining)}")
for f in remaining:
    print(f"  {f}")
