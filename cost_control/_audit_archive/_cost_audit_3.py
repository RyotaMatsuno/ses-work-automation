import sys, os, json, glob, datetime, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
out = []
def w(*a): out.append(" ".join(str(x) for x in a))

# A. find every cost ledger jsonl
w("=== COST LEDGER FILES ===")
for p in glob.glob(os.path.join(BASE,"**","cost_log*.jsonl"), recursive=True) + \
         glob.glob(os.path.join(BASE,"**","*ledger*.jsonl"), recursive=True) + \
         glob.glob(os.path.join(BASE,"**","cost*.jsonl"), recursive=True):
    try:
        lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
        w(f"\nFILE: {p.replace(BASE,'')}  ({len(lines)} lines)")
        for ln in lines[-25:]:
            w("  ", ln[:200])
    except Exception as e:
        w("ERR", p, e)

# B. does PRODUCTION mail_pipeline.py / matching_v2 / skill_judge enforce a cap?
w("\n=== DOES PRODUCTION CODE IMPORT/USE cost_guard? ===")
for f in ["mail_pipeline.py", os.path.join("matching_v2","matching_v2.py"),
          os.path.join("matching_v2","skill_judge.py")]:
    p = os.path.join(BASE, f)
    if not os.path.exists(p):
        w(f"{f}: NOT FOUND"); continue
    txt = open(p, encoding="utf-8", errors="replace").read()
    has_guard = ("cost_guard" in txt) or ("CostGuard" in txt) or ("DAILY" in txt and "LIMIT" in txt)
    plimit = re.findall(r"PROCESS_LIMIT\s*=\s*\S+", txt)
    maxtok = re.findall(r"max_tokens\s*=\s*\d+", txt)
    model  = re.findall(r'model"?\s*[:=]\s*["\']([\w\-.]+)', txt)
    bodylim= re.findall(r"\[:\s*(\d{3,6})\s*\]", txt)  # body truncation like body[:5000]
    w(f"\n{f}: cost_guard用={has_guard}")
    w(f"   PROCESS_LIMIT={plimit}")
    w(f"   max_tokens={sorted(set(maxtok))}")
    w(f"   model指定={sorted(set(model))[:6]}")
    w(f"   本文truncate候補(body[:N])={sorted(set(bodylim))[:10]}")

# C. mail_pipeline.log: today's activity volume + tail
w("\n=== mail_pipeline.log: TODAY volume + tail ===")
mp = os.path.join(BASE,"mail_pipeline","pipeline.log")
if os.path.exists(mp):
    sz = os.path.getsize(mp)
    w(f"size={sz} bytes ({sz/1e6:.1f} MB)")
    # read tail efficiently
    with open(mp, "rb") as fh:
        fh.seek(max(0, sz-120000))
        tail = fh.read().decode("utf-8", errors="replace")
    lines = tail.splitlines()
    today = "2026-06-05"
    today_lines = [l for l in lines if today in l]
    w(f"tail-window lines mentioning {today}: {len(today_lines)}")
    # count keywords across tail window
    for kw in ["処理", "件", "Batch", "batch", "classify", "ERROR", "error", "コスト", "cost", "skip", "スキップ", "新規"]:
        c = sum(1 for l in lines if kw in l)
        if c: w(f"   tail kw[{kw}]={c}")
    w("--- last 25 lines ---")
    for l in lines[-25:]:
        w("  ", l[:180])

# D. daily report log
w("\n=== daily_report.log tail ===")
dr = os.path.join(BASE,"logs","daily_report.log")
if os.path.exists(dr):
    t = open(dr, encoding="utf-8", errors="replace").read().splitlines()
    for l in t[-30:]:
        w("  ", l[:180])

with open(os.path.join(BASE,"_cost_audit_3.txt"),"w",encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("DONE")
