import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# SES_MatchingV3とSES_MailPipelineの直近実行結果確認
print("=== スケジューラ直近実行状況 ===")
for t in ["SES_MailPipeline", "SES_MatchingV3"]:
    r = subprocess.run(
        ["schtasks", "/query", "/tn", t, "/fo", "LIST", "/v"],
        capture_output=True,
        text=True,
        encoding="cp932",
        errors="replace",
    )
    lines = r.stdout.splitlines()
    keys = ["次回の実行時刻", "最終実行時刻", "最終結果", "状態"]
    print(f"\n  [{t}]")
    for l in lines:
        if any(k in l for k in keys):
            print(f"    {l.strip()}")

# weekday_guard経由になってからwd_batを直接テスト実行してみる
print("\n=== wd_matching_v3.bat の内容確認 ===")
bat = base / "wd_matching_v3.bat"
print(bat.read_text(encoding="utf-8", errors="replace"))

# weekday_guardが正しく呼び出せるか確認（dry-run）
print("\n=== weekday_guard 平日チェック（今日=平日） ===")
r2 = subprocess.run(
    ["python", "weekday_guard.py", "python", "-c", "print('matching_v3 would run')"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=str(base),
)
print(f"  stdout: {r2.stdout.strip()}")
print(f"  returncode: {r2.returncode}")
