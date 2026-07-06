import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os
import glob

SES = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# 1. pending_tasks status
print("=== PENDING TASKS ===")
pt = os.path.join(SES, "pending_tasks")
for f in sorted(os.listdir(pt)):
    if f.startswith('.') or f.startswith('_'):
        continue
    print(f"  {f}")

# 2. done_tasks status
print("\n=== DONE TASKS ===")
dt = os.path.join(SES, "done_tasks")
if os.path.exists(dt):
    for f in sorted(os.listdir(dt)):
        if f.startswith('.'):
            continue
        print(f"  {f}")
else:
    print("  (not found)")

# 3. Check what matching_v3 files changed recently
print("\n=== MATCHING_V3 RECENT CHANGES ===")
m3 = os.path.join(SES, "matching_v3")
if os.path.exists(m3):
    files = []
    for f in os.listdir(m3):
        fp = os.path.join(m3, f)
        if os.path.isfile(fp):
            mtime = os.path.getmtime(fp)
            files.append((f, mtime))
    files.sort(key=lambda x: x[1], reverse=True)
    for f, mt in files[:10]:
        from datetime import datetime
        t = datetime.fromtimestamp(mt).strftime("%m/%d %H:%M")
        print(f"  {t} - {f}")

# 4. Check scripts/ directory
print("\n=== SCRIPTS/ STATUS ===")
sc = os.path.join(SES, "scripts")
if os.path.exists(sc):
    for f in sorted(os.listdir(sc)):
        fp = os.path.join(sc, f)
        if os.path.isfile(fp):
            from datetime import datetime
            t = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%m/%d %H:%M")
            print(f"  {t} - {f}")

# 5. Check backfill_logs
print("\n=== BACKFILL LOGS ===")
bl = os.path.join(SES, "backfill_logs")
if os.path.exists(bl):
    for f in sorted(os.listdir(bl)):
        fp = os.path.join(bl, f)
        sz = os.path.getsize(fp) if os.path.isfile(fp) else 0
        print(f"  {f} ({sz/1024:.1f}KB)")
else:
    print("  (not found)")

# 6. Check if matching hardfilter config exists
print("\n=== MATCHING CONFIG ===")
cfg = os.path.join(m3, "config.py")
if os.path.exists(cfg):
    with open(cfg, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    if 'HARD_FILTERS' in content:
        print("  config.py has HARD_FILTERS")
    else:
        print("  config.py exists but no HARD_FILTERS")
else:
    print("  config.py not found")

# 7. Check extractors
print("\n=== EXTRACTORS STATUS ===")
ex = os.path.join(SES, "extractors")
if os.path.exists(ex):
    for f in sorted(os.listdir(ex)):
        fp = os.path.join(ex, f)
        if os.path.isfile(fp):
            from datetime import datetime
            t = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%m/%d %H:%M")
            sz = os.path.getsize(fp)
            print(f"  {t} - {f} ({sz/1024:.1f}KB)")
