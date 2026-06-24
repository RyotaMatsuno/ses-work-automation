import glob
import json
import os
import subprocess
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
today = date.today()

print("=" * 60)
print(f"【ジョブズ 全システム定期チェック】{today}")
print("=" * 60)

# ── 1. matching_v3 最新ログ ──────────────────────────
print("\n■ 1. matching_v3 最新ログ")
log_dir = os.path.join(SES, "matching_v3", "logs")
if os.path.isdir(log_dir):
    logs = sorted(glob.glob(os.path.join(log_dir, "*.log")), reverse=True)[:3]
    if logs:
        for lf in logs:
            print(f"  {os.path.basename(lf)}")
        with open(logs[0], encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        tail = lines[-60:] if len(lines) > 60 else lines
        print(f"\n  --- {os.path.basename(logs[0])} 末尾{len(tail)}行 ---")
        for l in tail:
            print("  " + l.rstrip())
    else:
        print("  ログファイルなし")
else:
    print(f"  未存在: {log_dir}")

# ── 2. mail_pipeline ログ ────────────────────────────
print("\n■ 2. mail_pipeline 最新ログ")
for search_dir in [os.path.join(SES, "logs"), SES]:
    mp_logs = sorted(glob.glob(os.path.join(search_dir, "mail_pipeline*.log")), reverse=True)[:2]
    if mp_logs:
        for lf in mp_logs:
            print(f"  {lf}")
        with open(mp_logs[0], encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        tail = lines[-30:] if len(lines) > 30 else lines
        print(f"\n  --- 末尾{len(tail)}行 ---")
        for l in tail:
            print("  " + l.rstrip())
        break
else:
    print("  mail_pipeline ログなし")

# ── 3. flag_auto_updater ログ ────────────────────────
print("\n■ 3. flag_auto_updater 最新ログ")
fu_log_dir = os.path.join(SES, "flag_auto_updater", "logs")
if os.path.isdir(fu_log_dir):
    fu_logs = sorted(glob.glob(os.path.join(fu_log_dir, "*.log")), reverse=True)[:2]
    if fu_logs:
        for lf in fu_logs:
            print(f"  {os.path.basename(lf)}")
        with open(fu_logs[0], encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        tail = lines[-20:] if len(lines) > 20 else lines
        print(f"\n  --- 末尾{len(tail)}行 ---")
        for l in tail:
            print("  " + l.rstrip())
    else:
        print("  ログなし")
else:
    print(f"  未存在: {fu_log_dir}")

# ── 4. mail_attachment_importer ログ ─────────────────
print("\n■ 4. mail_attachment_importer 最新ログ")
mai_log_dir = os.path.join(SES, "mail_attachment_importer", "logs")
if os.path.isdir(mai_log_dir):
    mai_logs = sorted(glob.glob(os.path.join(mai_log_dir, "*.log")), reverse=True)[:2]
    if mai_logs:
        for lf in mai_logs:
            print(f"  {os.path.basename(lf)}")
        with open(mai_logs[0], encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        tail = lines[-20:] if len(lines) > 20 else lines
        print(f"\n  --- 末尾{len(tail)}行 ---")
        for l in tail:
            print("  " + l.rstrip())
    else:
        print("  ログなし")
else:
    print(f"  未存在: {mai_log_dir}")

# ── 5. CostGuard state ───────────────────────────────
print("\n■ 5. CostGuard 使用量")
found_cg = False
for root, dirs, files in os.walk(SES):
    dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", "node_modules"]]
    for fn in files:
        if "cost_guard" in fn.lower() and fn.endswith(".json"):
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, SES)
            try:
                with open(fp, encoding="utf-8", errors="replace") as f:
                    cg = json.load(f)
                print(f"  [{rel}] {json.dumps(cg, ensure_ascii=False)}")
                found_cg = True
            except:
                print(f"  [{rel}] 読み取り失敗")
if not found_cg:
    print("  cost_guard_state.json 未存在（まだコストゼロ or 別名）")

# ── 6. タスクスケジューラ ─────────────────────────────
print("\n■ 6. タスクスケジューラ 直近実行")
tasks = ["SES_MailPipeline", "SES_MatchingV3", "line_bridge_worker_health", "jobz_importer", "usage_tracker_daily"]
for t in tasks:
    try:
        r = subprocess.run(
            ["schtasks", "/Query", "/TN", t, "/FO", "LIST"],
            capture_output=True,
            text=True,
            encoding="cp932",
            errors="replace",
            timeout=10,
        )
        if r.returncode == 0:
            info = {}
            for line in r.stdout.strip().split("\n"):
                for key in ["最終実行時刻", "次回実行時刻", "状態", "最終結果"]:
                    if key in line:
                        info[key] = line.split(":", 1)[-1].strip()
            print(
                f"  [{t}] 最終:{info.get('最終実行時刻', '?')} 結果:{info.get('最終結果', '?')} 次回:{info.get('次回実行時刻', '?')}"
            )
        else:
            print(f"  [{t}] 未登録")
    except Exception as e:
        print(f"  [{t}] エラー: {e}")

# ── 7. run_flag_updater import確認 ───────────────────
print("\n■ 7. run_flag_updater.py import確認")
rfu = os.path.join(SES, "flag_auto_updater", "run_flag_updater.py")
if os.path.exists(rfu):
    with open(rfu, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if "import" in line and ("notion" in line.lower() or "rule" in line.lower()):
                print(f"  L{i}: {line.rstrip()}")
else:
    print("  ファイル未存在")

print("\n" + "=" * 60)
print("チェック完了")
print("=" * 60)
