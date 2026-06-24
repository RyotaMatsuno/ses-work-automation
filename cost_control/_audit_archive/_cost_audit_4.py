import glob
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
out = []


def w(*a):
    out.append(" ".join(str(x) for x in a))


# 1. cost log sums
def summarize(path):
    agg = {}
    days = set()
    tot = 0.0
    for ln in open(path, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except:
            continue
        k = (d.get("script"), d.get("model"))
        a = agg.setdefault(k, {"n": 0, "in": 0, "out": 0, "usd": 0.0})
        a["n"] += 1
        a["in"] += d.get("input_tokens", 0)
        a["out"] += d.get("output_tokens", 0)
        a["usd"] += d.get("cost_usd", 0.0)
        tot += d.get("cost_usd", 0.0)
        if d.get("ts"):
            days.add(d["ts"][:10])
    return agg, tot, days


for f in [
    "usage_tracker/cost_log_archive_2026-06.jsonl",
    "usage_tracker/cost_log.jsonl",
    "usage_tracker/cost_log_archive_2026-05.jsonl",
]:
    p = os.path.join(BASE, f)
    if not os.path.exists(p):
        w(f"\n## {f}: NOT FOUND")
        continue
    try:
        agg, tot, days = summarize(p)
        w(f"\n## {f}")
        w(f"  日付: {sorted(days)}  合計 ${tot:.2f} (¥{tot * 155:.0f})")
        for k, a in sorted(agg.items(), key=lambda x: -x[1]["usd"]):
            w(f"   {str(k[0]):14}{str(k[1]):28} n{a['n']:>6} in{a['in']:>10} out{a['out']:>9} ${a['usd']:.2f}")
    except Exception as e:
        w(f"## {f} ERR {e}")

# 2. locate mail_pipeline.py
w("\n=== locate mail_pipeline.py ===")
cands = glob.glob(os.path.join(BASE, "**", "mail_pipeline*.py"), recursive=True)
for c in cands[:10]:
    w("  ", c.replace(BASE, ""), os.path.getsize(c), "B")
# pick the production one (largest non-test in mail_pipeline dir or root)
prod = None
for c in cands:
    if c.endswith("mail_pipeline.py"):
        prod = c
        break
if not prod and cands:
    prod = max(cands, key=os.path.getsize)
w("  -> chosen:", prod.replace(BASE, "") if prod else None)

if prod:
    txt = open(prod, encoding="utf-8", errors="replace").read()
    w("  -- ingest/limit/broadcast filter --")
    for kw in [
        "PROCESS_LIMIT",
        "LIMIT =",
        "配信",
        "出回",
        "一斉",
        "broadcast",
        "スキップ",
        "除外",
        "body[:",
        "本文[:",
        "671",
        "名分",
        "skill_judge",
        "判定",
    ]:
        for i, l in enumerate(txt.splitlines(), 1):
            if kw in l and not l.strip().startswith("#"):
                w(f"   [{kw}] {i}: {l.strip()[:120]}")
                break

# 3. importer.log tail
w("\n=== importer.log tail ===")
ip = os.path.join(BASE, "mail_attachment_importer", "importer.log")
if os.path.exists(ip):
    sz = os.path.getsize(ip)
    with open(ip, "rb") as fh:
        fh.seek(max(0, sz - 25000))
        t = fh.read().decode("utf-8", errors="replace")
    L = t.splitlines()
    w(f"  size={sz}B  limit-hits-in-tail={sum(1 for l in L if 'limit' in l.lower() or '上限' in l)}")
    for l in L[-10:]:
        w("   ", l[:150])

# 4. scheduled tasks
w("\n=== scheduled tasks (filtered) ===")
try:
    r = subprocess.run(
        ["schtasks", "/query", "/fo", "csv", "/nh"], capture_output=True, text=True, encoding="cp932", errors="replace"
    )
    for line in (r.stdout or "").splitlines():
        if any(
            k in line
            for k in ["SES", "ses_", "freee", "usage", "Matching", "Mail", "attachment", "watchdog", "daily", "cost"]
        ):
            w("   ", line[:150])
except Exception as e:
    w("  schtasks ERR", e)

with open(os.path.join(BASE, "_cost_audit_4.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("DONE")
