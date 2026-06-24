import os
import shutil
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
base = os.getcwd()
today = datetime.now().strftime("%Y%m%d")

# Archive and trim huge logs
ops = [
    # (path, action, keep_lines)
    ("matching_v3/logs/match_results_bak.jsonl", "delete_if_over_mb", 50),  # > 50MB → delete
    ("matching_v3/logs/match_results.jsonl", "trim_tail", 2000),  # keep last 2000 lines
    ("mail_pipeline/pipeline.log", "trim_tail", 5000),  # keep last 5000 lines
]
for path, action, threshold in ops:
    p = os.path.join(base, path)
    if not os.path.isfile(p):
        print(f"  SKIP (not found): {path}")
        continue
    sz = os.path.getsize(p) / (1024 * 1024)
    print(f"  {path}: {sz:.1f}MB → action={action}")
    if action == "delete_if_over_mb":
        if sz > threshold:
            arc = p + f".bak_{today}"
            os.rename(p, arc)
            # recreate empty
            open(p, "w", encoding="utf-8").write("")
            print(f"    archived to {os.path.basename(arc)}, created fresh empty file")
        else:
            print(f"    under {threshold}MB, skip")
    elif action == "trim_tail":
        with open(p, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if len(lines) > threshold:
            arc = p + f".bak_{today}"
            shutil.copy2(p, arc)
            open(p, "w", encoding="utf-8").writelines(lines[-threshold:])
            new_sz = os.path.getsize(p) / (1024 * 1024)
            print(f"    trimmed {len(lines)} → {threshold} lines ({new_sz:.1f}MB). archived original.")
        else:
            print(f"    only {len(lines)} lines, no trim needed")

# cost_log.jsonl: just report size (don't trim — it's the audit trail; only if truly massive)
cl = os.path.join(base, "usage_tracker", "cost_log.jsonl")
if os.path.isfile(cl):
    print(f"\n  cost_log.jsonl: {os.path.getsize(cl) / 1024 / 1024:.1f}MB — audit trail, keeping as-is")
print("\ndone")
