import datetime
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
out = []


def w(*a):
    out.append(" ".join(str(x) for x in a))


# 1. matching_v2 git state (disabled or re-enabled?)
w("=== matching_v2 git log (last 8) ===")
try:
    r = subprocess.run(
        ["git", "-C", os.path.join(BASE, "matching_v2"), "log", "--oneline", "-8"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    w(r.stdout or r.stderr)
except Exception as e:
    w("ERR", e)

# repo-level git log (maybe matching_v2 is not its own repo)
w("=== repo git log (last 12) ===")
try:
    r = subprocess.run(
        ["git", "-C", BASE, "log", "--oneline", "-12"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    w(r.stdout or r.stderr)
except Exception as e:
    w("ERR", e)

# 2. find all log files, sizes + mtime, sorted by mtime desc
w("\n=== LOG FILES (mtime desc) ===")
logs = []
for root, dirs, files in os.walk(BASE):
    if ".git" in root or "node_modules" in root:
        continue
    for f in files:
        if f.endswith(".log") or "log" in f.lower() and f.endswith(".txt"):
            p = os.path.join(root, f)
            try:
                st = os.stat(p)
                logs.append((st.st_mtime, st.st_size, p.replace(BASE, "")))
            except:
                pass
logs.sort(reverse=True)
for m, sz, p in logs[:30]:
    w(f"{datetime.datetime.fromtimestamp(m):%Y-%m-%d %H:%M}  {sz:>10}B  {p}")

# 3. grep for cost cap / budget enforcement across py files
w("\n=== COST CAP / BUDGET ENFORCEMENT (grep) ===")
patt = ["daily_cap", "DAILY_CAP", "budget", "BUDGET", "cost_limit", "COST_LIMIT", "6.0", "max_cost", "stop_if", "上限"]
hits = 0
for root, dirs, files in os.walk(BASE):
    if ".git" in root or "node_modules" in root:
        continue
    for f in files:
        if not f.endswith(".py"):
            continue
        p = os.path.join(root, f)
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except:
            continue
        for ln_no, line in enumerate(txt.splitlines(), 1):
            for kw in patt:
                if kw in line and not line.strip().startswith("#"):
                    w(f"{f}:{ln_no}: {line.strip()[:100]}")
                    hits += 1
                    break
w(f"-- cap-related hits: {hits}")

# 4. count active anthropic API call sites
w("\n=== ANTHROPIC API CALL SITES (active, non-comment) ===")
for root, dirs, files in os.walk(BASE):
    if ".git" in root or "node_modules" in root:
        continue
    for f in files:
        if not f.endswith(".py"):
            continue
        p = os.path.join(root, f)
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except:
            continue
        for ln_no, line in enumerate(txt.splitlines(), 1):
            s = line.strip()
            if ("messages.create" in s or "client.messages" in s or "anthropic" in s.lower()) and not s.startswith("#"):
                w(f"{f}:{ln_no}: {s[:110]}")

with open(os.path.join(BASE, "_cost_audit_2.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("DONE")
