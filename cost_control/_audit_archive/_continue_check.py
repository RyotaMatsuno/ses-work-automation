import sys, os, re, glob, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
out=[]
def w(*a): out.append(" ".join(str(x) for x in a))

# 1. finalizer report (full) + prune tail
w("=== FINALIZER REPORT ===")
fr=os.path.join(BASE,"_finalizer_report.txt")
w(open(fr,encoding="utf-8",errors="replace").read().strip() if os.path.exists(fr) else "(none)")
w("\n=== PRUNE tail3 ===")
pp=os.path.join(BASE,"_prune_progress.txt")
w("\n".join(open(pp,encoding="utf-8",errors="replace").read().splitlines()[-3:]) if os.path.exists(pp) else "(none)")

# 2. broadcast filter live in pipeline.log (tail window)
w("\n=== pipeline.log: broadcast filter activity (tail) ===")
mp=os.path.join(BASE,"mail_pipeline","pipeline.log")
if os.path.exists(mp):
    sz=os.path.getsize(mp)
    with open(mp,"rb") as fh: fh.seek(max(0,sz-200000)); t=fh.read().decode("utf-8",errors="replace")
    L=t.splitlines()
    starts=[l for l in L if "起動" in l or "v5.1" in l or "パイプライン" in l]
    excl=[l for l in L if "配信除外" in l]
    cls=[l for l in L if "分類対象" in l]
    w(f"  最新起動行: {starts[-1].strip()[:120] if starts else '(なし)'}")
    w(f"  配信除外ログ件数(tail): {len(excl)}")
    for l in excl[-6:]: w("    "+l.strip()[:120])
    w(f"  分類対象サマリ行(最新3):")
    for l in cls[-3:]: w("    "+l.strip()[:120])
else:
    w("  pipeline.log なし")

# 3. is double_check active? who imports/calls it
w("\n=== double_check 利用箇所 (who imports/calls) ===")
hits=0
for p in glob.glob(os.path.join(BASE,"**","*.py"),recursive=True):
    rel=p.replace(BASE,"")
    if "_archive" in rel or rel.endswith("double_check.py"): continue
    try: t=open(p,encoding="utf-8",errors="replace").read()
    except: continue
    for i,l in enumerate(t.splitlines(),1):
        s=l.strip()
        if s.startswith("#"): continue
        if "double_check" in l.lower() and ("import" in l or "from" in l or "double_check(" in l.lower() or "run_double" in l.lower()):
            w(f"  {rel}:{i}: {s[:110]}"); hits+=1
w(f"  -- 参照箇所: {hits}件")
# is double_check in any scheduled task?
q=subprocess.run(["schtasks","/query","/fo","csv","/nh"],capture_output=True,text=True,encoding="cp932",errors="replace")
dc_task=[ln for ln in (q.stdout or "").splitlines() if "double" in ln.lower() or "check" in ln.lower()]
w(f"  double_check関連タスク: {dc_task if dc_task else 'なし'}")

with open(os.path.join(BASE,"_continue_check.txt"),"w",encoding="utf-8") as f:
    f.write("\n".join(out))
print("DONE")
