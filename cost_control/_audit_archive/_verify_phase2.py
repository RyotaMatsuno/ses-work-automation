import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
out = []


def w(*a):
    out.append(" ".join(str(x) for x in a))


# 1. is_broadcast full function
w("=== is_broadcast() in mail_pipeline.py ===")
mp = os.path.join(BASE, "mail_pipeline", "mail_pipeline.py")
lines = open(mp, encoding="utf-8", errors="replace").read().splitlines()
start = None
for i, l in enumerate(lines):
    if re.match(r"\s*def is_broadcast", l):
        start = i
        break
if start is not None:
    depth_done = False
    for j in range(start, min(start + 70, len(lines))):
        w(f"  {j + 1}: {lines[j].rstrip()[:130]}")
        if j > start and re.match(r"\s*def ", lines[j]) and j != start:
            break
else:
    w("  is_broadcast NOT FOUND")
# constants
w("\n  -- limits/allowlist constants --")
for i, l in enumerate(lines, 1):
    if re.search(
        r"(FETCH_LIMIT|CLASSIFY_LIMIT|PROCESS_LIMIT|BROADCAST_SENDER_ALLOWLIST|RECIPIENT)", l
    ) and not l.strip().startswith("#"):
        w(f"  {i}: {l.strip()[:120]}")

# 2. project_expiry.py full (small)
w("\n=== project_expiry.py (full) ===")
pe = os.path.join(BASE, "cost_control", "project_expiry.py")
if os.path.exists(pe):
    pet = open(pe, encoding="utf-8", errors="replace").read()
    w(f"  ({len(pet.splitlines())} lines)")
    for i, l in enumerate(pet.splitlines(), 1):
        w(f"  {i}: {l.rstrip()[:130]}")
else:
    w("  NOT FOUND")

with open(os.path.join(BASE, "_verify_phase2.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(
    "DONE lines_pe=", len(open(pe, encoding="utf-8", errors="replace").read().splitlines()) if os.path.exists(pe) else 0
)
