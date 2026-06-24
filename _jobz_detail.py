import glob
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()

# ── matching_v3 ログ詳細 ─────────────────────────────
print("■ matching_v3 ログ全ファイルリスト + phase0内容")
log_dir = os.path.join(SES, "matching_v3", "logs")
if os.path.isdir(log_dir):
    all_logs = sorted(
        glob.glob(os.path.join(log_dir, "**", "*.log"), recursive=True) + glob.glob(os.path.join(log_dir, "*.log")),
        reverse=True,
    )
    all_logs = list(dict.fromkeys(all_logs))
    for lf in all_logs:
        size = os.path.getsize(lf)
        mtime = os.path.getmtime(lf)
        from datetime import datetime

        print(f"  {os.path.basename(lf)} size={size}bytes mtime={datetime.fromtimestamp(mtime)}")

    # phase0_stdout_final.log の中身（空の場合は別ログを探す）
    for lf in all_logs:
        sz = os.path.getsize(lf)
        if sz > 0:
            print(f"\n  --- {os.path.basename(lf)} (全{sz}bytes) ---")
            with open(lf, encoding="utf-8", errors="replace") as f:
                content = f.read()
            print(content[:3000])
            break

    # matching_v3直下の.logも確認
    direct_logs = glob.glob(os.path.join(SES, "matching_v3", "*.log"))
    if direct_logs:
        for lf in sorted(direct_logs, reverse=True)[:3]:
            sz = os.path.getsize(lf)
            print(f"\n  [直下] {os.path.basename(lf)} size={sz}")
            if sz > 0:
                with open(lf, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                for l in lines[-40:]:
                    print("  " + l.rstrip())
else:
    print("  logs/ 未存在")

# ── mail_pipeline ログ探索 ────────────────────────────
print("\n■ mail_pipeline ログ探索（全ses_work）")
mp_logs = []
for root, dirs, files in os.walk(SES):
    dirs[:] = [d for d in dirs if d not in [".git", "__pycache__"]]
    for fn in files:
        if "mail" in fn.lower() and fn.endswith(".log"):
            mp_logs.append(os.path.join(root, fn))
if mp_logs:
    for lf in sorted(mp_logs, key=os.path.getmtime, reverse=True)[:5]:
        sz = os.path.getsize(lf)
        print(f"  {os.path.relpath(lf, SES)} size={sz}")
    # 最新を表示
    latest = sorted(mp_logs, key=os.path.getmtime, reverse=True)[0]
    if os.path.getsize(latest) > 0:
        with open(latest, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        print(f"\n  --- {os.path.relpath(latest, SES)} 末尾30行 ---")
        for l in lines[-30:]:
            print("  " + l.rstrip())
else:
    print("  mail系ログなし")

# ── mail_attachment_importer ─────────────────────────
print("\n■ mail_attachment_importer ディレクトリ構成")
mai_dir = os.path.join(SES, "mail_attachment_importer")
if os.path.isdir(mai_dir):
    for root, dirs, files in os.walk(mai_dir):
        dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git"]]
        level = root.replace(mai_dir, "").count(os.sep)
        indent = "  " * (level + 1)
        print(f"{indent}{os.path.basename(root)}/")
        for fn in files:
            fp = os.path.join(root, fn)
            sz = os.path.getsize(fp)
            print(f"{indent}  {fn} ({sz}b)")
else:
    print("  ディレクトリ未存在")

# ── タスクスケジューラ 詳細（英語キー対応）─────────────
print("\n■ タスクスケジューラ 詳細")
tasks = ["SES_MailPipeline", "SES_MatchingV3", "line_bridge_worker_health", "jobz_importer", "usage_tracker_daily"]
for t in tasks:
    r = subprocess.run(
        ["schtasks", "/Query", "/TN", t, "/FO", "LIST", "/V"],
        capture_output=True,
        text=True,
        encoding="cp932",
        errors="replace",
        timeout=10,
    )
    if r.returncode == 0:
        lines = r.stdout.strip().split("\n")
        info = {}
        for line in lines:
            for key in [
                "最終実行時刻",
                "次回実行時刻",
                "状態",
                "最終結果",
                "Last Run Time",
                "Next Run Time",
                "Status",
                "Last Result",
            ]:
                if ":" in line and key in line:
                    info[key] = line.split(":", 1)[-1].strip()
        print(f"  [{t}]")
        for k, v in info.items():
            print(f"    {k}: {v}")
    else:
        print(f"  [{t}] 未登録 or エラー: {r.stderr[:100]}")
