# -*- coding: utf-8 -*-
import datetime
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
CODEX = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
REP = os.path.join(BASE, "_audit_fix_report.txt")
ARCH = os.path.join(BASE, "cost_control", "_audit_archive")


def rep(m):
    with open(REP, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%H:%M:%S} {m}\n")


open(REP, "w", encoding="utf-8").close()


def git(*a):
    return subprocess.run(["git", "-C", BASE, *a], capture_output=True, text=True, encoding="utf-8", errors="replace")


# step0: move broken scratch (#11)
import shutil

os.makedirs(ARCH, exist_ok=True)
for f in ["cleanup2.py", "inject_consts.py", "setup_drive_oauth.py"]:
    p = os.path.join(BASE, f)
    if os.path.exists(p):
        try:
            shutil.move(p, os.path.join(ARCH, f))
            rep(f"#11 moved {f}")
        except Exception as e:
            rep(f"#11 move fail {f}: {e}")

# step1: wait for Codex 3a (log stable >=45s with content)
log3a = os.path.join(BASE, "cost_control", "codex_phase3a.log")
last = -1
stable = 0
rep("waiting Codex Phase3a ...")
for _ in range(160):
    try:
        sz = os.path.getsize(log3a)
    except:
        sz = 0
    if sz == last and sz > 300:
        stable += 1
    else:
        stable = 0
        last = sz
    if stable >= 3:
        break
    time.sleep(15)
rep(f"Phase3a log stable size={last}")

# step2: py_compile changed files
changed = [
    "mail_attachment_importer/ai_extractor.py",
    "line_webhook/line_query.py",
    "mail_pipeline/mail_pipeline.py",
    "outlook/outlook_to_notion.py",
    "reply_parser/reply_parser.py",
    "mail_attachment_importer/importer.py",
    "mail_attachment_importer/mail_fetcher.py",
]
fail = []
for rel in changed:
    p = os.path.join(BASE, rel)
    if os.path.exists(p):
        r = subprocess.run(
            [sys.executable, "-m", "py_compile", p], capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        rep(f"compile {rel}: {'OK' if r.returncode == 0 else 'FAIL'}")
        if r.returncode != 0:
            fail.append((rel, (r.stderr or "")[:200]))
if fail:
    for rel, e in fail:
        rep(f"  FAIL {rel}: {e}")
    rep("Phase3a COMPILE FAIL -> commitせず停止。手動レビュー要")
    raise SystemExit(0)

# step3: commit 3a
git("add", *[c for c in changed if os.path.exists(os.path.join(BASE, c))], "cost_control")
c = git(
    "commit",
    "-m",
    "cost_control Phase3a: audit fixes F2(guard ai_extractor) F3(freshness created_time) F6(gross floor) F8(FETCH_LIMIT 200) F10(processed-id)",
)
rep("3a commit: " + ((c.stdout or c.stderr).splitlines()[-1] if (c.stdout or c.stderr) else "?"))

# step4: run Codex 3b synchronously (#5 fetch filter on line_query)
d31 = (datetime.date.today() - datetime.timedelta(days=31)).isoformat()
d10 = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
prompt3b = (
    "line_webhook/line_query.py のみ修正。目的: Notion全件取得を粗フィルタで削減(#5)。"
    "(1)engineer_query 内の fetch_all_pages(ENGINEER_DB_ID) を fetch_all_pages(ENGINEER_DB_ID, filter_body={'timestamp':'created_time','created_time':{'on_or_after':'"
    + d31
    + "'}}) に変更(エンジニアを直近約1ヶ月に粗絞り)。"
    "(2)project_query 内の fetch_all_pages(ENGINEER_DB_ID) も同様に created_time on_or_after '" + d31 + "' を付与。"
    "(3)engineer_query 内の projects 取得(既存_prj_filter rate>0)を {'and':[既存rateフィルタ, {'timestamp':'created_time','created_time':{'on_or_after':'"
    + d10
    + "'}}]} に。"
    "(4)project_query 内の projects 取得(既存status=募集中フィルタ)も {'and':[既存statusフィルタ, {'timestamp':'created_time','created_time':{'on_or_after':'"
    + d10
    + "'}}]} に。"
    "日付は上記固定文字列でよい。Python側の business_days_since による厳密チェックは一切変更しない(粗フィルタの後段でそのまま効かせる)。"
    "送信系に触れない。fetch_all_pages のシグネチャ(filter_body引数)は既存のものを使う。"
    "変更後 py_compile で確認し cost_control_phase3_compile.txt に追記。変更要約を出力。"
)
log3b = os.path.join(BASE, "cost_control", "codex_phase3b.log")
rep("launching Codex Phase3b (#5 fetch filter) synchronously ...")
try:
    r = subprocess.run(
        [CODEX, "exec", prompt3b, "-C", BASE, "--dangerously-bypass-approvals-and-sandbox"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        cwd=BASE,
    )
    open(log3b, "w", encoding="utf-8").write((r.stdout or "") + "\n---STDERR---\n" + (r.stderr or ""))
    rep(f"Phase3b finished rc={r.returncode}")
except subprocess.TimeoutExpired:
    rep("Phase3b TIMEOUT(600s) -> 後で確認")
except Exception as e:
    rep(f"Phase3b error: {e}")

# step5: verify+commit 3b
lq = os.path.join(BASE, "line_webhook", "line_query.py")
r = subprocess.run(
    [sys.executable, "-m", "py_compile", lq], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
rep(f"compile line_query: {'OK' if r.returncode == 0 else 'FAIL'}")
if r.returncode == 0:
    git("add", "line_webhook/line_query.py")
    c = git("commit", "-m", "cost_control Phase3b: line_query created_time pre-filter (#5)")
    rep("3b commit: " + ((c.stdout or c.stderr).splitlines()[-1] if (c.stdout or c.stderr) else "(no change?)"))
else:
    rep(f"line_query COMPILE FAIL: {(r.stderr or '')[:200]} -> 3b未コミット")

rep("=== AUDIT FINALIZER DONE ===")
