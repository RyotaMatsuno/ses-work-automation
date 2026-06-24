import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ses_work = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
log_path = ses_work / "mail_pipeline" / "pipeline.log"

with open(log_path, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# 今日のログを抽出
today_lines = [l for l in lines if "2026-06-04" in l]
print(f"今日のログ行数: {len(today_lines)}")

# エラー・例外系
errors = [
    l.strip()
    for l in today_lines
    if "error" in l.lower() or "exception" in l.lower() or "失敗" in l or "division" in l.lower()
]
print(f"\nエラー行数: {len(errors)}")
print("--- エラー一覧 ---")
for e in errors[:30]:
    print(e)

# processed_ids保存の成否
saves = [l.strip() for l in today_lines if "processed_id" in l.lower() or "保存" in l]
print(f"\nprocessed_id保存関連行数: {len(saves)}")
for s in saves[:10]:
    print(s)

# API呼び出し回数（Haiku使用）
api = [
    l
    for l in today_lines
    if "haiku" in l.lower()
    or "claude" in l.lower()
    or "classify" in l.lower()
    or "ai_matching" in l.lower()
    or "double_check" in l.lower()
]
print(f"\nAPI呼び出し関連行: {len(api)}")

# 何回「起動」したか
starts = [l.strip() for l in today_lines if "起動" in l]
print(f"\nパイプライン起動回数: {len(starts)}")
for s in starts:
    print(s)
