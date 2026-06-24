import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()

# ── matching_v3_20260610/11 ログ内容 ──────────────────
print("■ matching_v3 今日/昨日ログ内容")
for fname in ["matching_v3_20260611.log", "matching_v3_20260610.log"]:
    lf = os.path.join(SES, "matching_v3", "logs", fname)
    if os.path.exists(lf):
        sz = os.path.getsize(lf)
        print(f"\n--- {fname} size={sz} ---")
        if sz > 0:
            with open(lf, encoding="utf-8", errors="replace") as f:
                print(f.read())
        else:
            print("  (空ファイル)")

# ── matching_v3_20260609 末尾確認 ─────────────────────
print("\n■ matching_v3_20260609.log 末尾30行（前回の最後の状態）")
lf09 = os.path.join(SES, "matching_v3", "logs", "matching_v3_20260609.log")
if os.path.exists(lf09):
    with open(lf09, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    print(f"  総行数: {len(lines)}")
    for l in lines[-30:]:
        print("  " + l.rstrip())

# ── weekday_guard.py 確認 ─────────────────────────────
print("\n■ weekday_guard.py 内容")
wg = os.path.join(SES, "matching_v3", "weekday_guard.py")
if os.path.exists(wg):
    with open(wg, encoding="utf-8", errors="replace") as f:
        print(f.read())
else:
    print("  未存在")

# ── run_matching.py 内容 ──────────────────────────────
print("\n■ run_matching.py 内容")
rm = os.path.join(SES, "matching_v3", "run_matching.py")
if os.path.exists(rm):
    with open(rm, encoding="utf-8", errors="replace") as f:
        print(f.read())
else:
    print("  未存在")

# ── タスクスケジューラ 詳細（/V オプション）──────────
print("\n■ SES_MatchingV3 タスク詳細")
r = subprocess.run(
    ["schtasks", "/Query", "/TN", "SES_MatchingV3", "/FO", "LIST", "/V"],
    capture_output=True,
    text=True,
    encoding="cp932",
    errors="replace",
    timeout=10,
)
print(r.stdout[:3000])
if r.returncode != 0:
    print(f"エラー: {r.stderr}")

print("\n■ SES_MailPipeline タスク詳細")
r2 = subprocess.run(
    ["schtasks", "/Query", "/TN", "SES_MailPipeline", "/FO", "LIST", "/V"],
    capture_output=True,
    text=True,
    encoding="cp932",
    errors="replace",
    timeout=10,
)
print(r2.stdout[:3000])

# ── mail_pipeline.py のログ出力先確認 ─────────────────
print("\n■ mail_pipeline.py ログ設定確認")
mp = os.path.join(SES, "mail_pipeline.py")
if os.path.exists(mp):
    with open(mp, encoding="utf-8", errors="replace") as f:
        content = f.read()
    # ログ関連行を抽出
    for i, line in enumerate(content.split("\n"), 1):
        if any(kw in line.lower() for kw in ["logging", "log_file", "log_dir", "filehandler", "basicconfig"]):
            print(f"  L{i}: {line.rstrip()}")
else:
    print("  mail_pipeline.py 未存在")

# ── notion_client.py 提案対象フラグエラー確認 ─────────
print("\n■ notion_client.py 提案対象フラグフィルタ部分")
nc = os.path.join(SES, "matching_v3", "notion_client.py")
if os.path.exists(nc):
    with open(nc, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    # 提案対象フラグ周辺
    for i, line in enumerate(lines, 1):
        if "提案対象" in line or "flag" in line.lower() or "filter" in line.lower():
            ctx_start = max(0, i - 2)
            ctx_end = min(len(lines), i + 3)
            for j in range(ctx_start, ctx_end):
                print(f"  L{j + 1}: {lines[j].rstrip()}")
            print()
else:
    print("  未存在")
