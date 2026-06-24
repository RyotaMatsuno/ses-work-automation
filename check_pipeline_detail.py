# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\pipeline.log")
lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
today = "2026-06-15"
today_lines = [l for l in lines if l.startswith(f"[{today}")]

# 処理対象メール数（fetch件数）
fetched = [l for l in today_lines if "fetch" in l.lower() or "取得" in l or "件取得" in l or "メール取得" in l]
print("=== fetch関連ログ ===")
for l in fetched[:20]:
    print(f"  {l[:120]}")

# アカウント別処理状況
print("\n=== アカウント別ログ ===")
for acc in ["sessales", "matsuno", "okamoto"]:
    acc_lines = [l for l in today_lines if acc in l.lower()]
    print(f"  {acc}: {len(acc_lines)}件関連ログ")
    for l in acc_lines[:3]:
        print(f"    {l[:100]}")

# 全体サマリー行
print("\n=== サマリー行 ===")
for l in today_lines:
    if "合計" in l or "全体" in l or "total" in l.lower() or "完了" in l or "処理件数" in l or "====" in l:
        print(f"  {l[:120]}")

# 最初と最後の数行
print("\n=== 今日の最初10行 ===")
for l in today_lines[:10]:
    print(f"  {l[:120]}")

print("\n=== 今日の最後10行 ===")
for l in today_lines[-10:]:
    print(f"  {l[:120]}")
