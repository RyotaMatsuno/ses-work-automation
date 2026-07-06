import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"
os.makedirs(PENDING, exist_ok=True)

# Check existing files
existing = os.listdir(PENDING)
print(f"Existing pending_tasks: {len(existing)}")
for f in existing:
    print(f"  {f}")
