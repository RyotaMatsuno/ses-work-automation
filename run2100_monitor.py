import datetime
import glob
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
REP = os.path.join(BASE, "_run2100_report.txt")


def rep(m):
    with open(REP, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%H:%M:%S} {m}\n")


open(REP, "w", encoding="utf-8").close()

# wait until 21:06
target = datetime.datetime.now().replace(hour=21, minute=6, second=0, microsecond=0)
if datetime.datetime.now() < target:
    rep(f"21:00監視 待機開始 -> {target:%H:%M}まで")
    time.sleep(max(0, (target - datetime.datetime.now()).total_seconds()))
rep("=== 21:00稼働 結果キャプチャ ===")

# 1) mail_pipeline broadcast filter result (today >= 20:55)
mp = os.path.join(BASE, "mail_pipeline", "pipeline.log")
today = datetime.date.today().isoformat()
excl = 0
start = None
cls = None
errs = 0
try:
    with open(mp, encoding="utf-8", errors="replace") as f:
        for line in f:
            if today in line and (" 20:5" in line or " 21:" in line):
                if "起動" in line:
                    start = line.strip()
                if "配信除外" in line:
                    excl += 1
                if "分類対象" in line:
                    cls = line.strip()
                if "ERROR" in line or "失敗" in line:
                    errs += 1
    rep(f"[mail_pipeline] 起動行: {start[:110] if start else '(21時台の起動なし)'}")
    rep(f"[mail_pipeline] 配信除外件数(21時台): {excl}")
    rep(f"[mail_pipeline] 分類対象サマリ: {cls[:110] if cls else '(なし)'}")
    rep(f"[mail_pipeline] エラー/失敗行(21時台): {errs}")
except Exception as e:
    rep(f"[mail_pipeline] 読込err {e}")

# 2) matching_v3 freshest log + result
v3dir = os.path.join(BASE, "matching_v3")
try:
    logs = sorted(
        glob.glob(os.path.join(v3dir, "*.log")) + glob.glob(os.path.join(v3dir, "*.txt")),
        key=os.path.getmtime,
        reverse=True,
    )
    if logs:
        p = logs[0]
        sz = os.path.getsize(p)
        with open(p, "rb") as fh:
            fh.seek(max(0, sz - 2000))
            tail = fh.read().decode("utf-8", errors="replace")
        rep(f"[v3] 最新ログ {os.path.basename(p)} tail:")
        for l in tail.splitlines()[-12:]:
            rep("   " + l[:120])
    else:
        rep("[v3] ログ未検出")
    rj = os.path.join(v3dir, "result.json")
    if os.path.exists(rj):
        d = json.load(open(rj, encoding="utf-8", errors="replace"))
        n = len(d) if isinstance(d, list) else len(d.get("results", d)) if isinstance(d, dict) else "?"
        rep(f"[v3] result.json 件数: {n} (mtime {datetime.datetime.fromtimestamp(os.path.getmtime(rj)):%H:%M})")
except Exception as e:
    rep(f"[v3] err {e}")

# 3) today's evening API spend (cost_log)
try:
    cl = os.path.join(BASE, "usage_tracker", "cost_log.jsonl")
    tot = 0.0
    n = 0
    if os.path.exists(cl):
        for ln in open(cl, encoding="utf-8", errors="replace"):
            try:
                d = json.loads(ln)
            except:
                continue
            ts = d.get("ts", "")
            if ts[:10] == today and ts[11:13] in ("20", "21", "22"):
                tot += d.get("cost_usd", 0.0)
                n += 1
    rep(f"[cost] 本日20-22時のAPI課金: ${tot:.4f} ({n}コール) ※$1/日ガード下")
except Exception as e:
    rep(f"[cost] err {e}")

rep("=== 監視完了。次回チャットで _run2100_report.txt を確認 ===")
print("21:00 monitor logic done (normally detached)")
