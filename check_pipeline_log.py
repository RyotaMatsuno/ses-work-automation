# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\pipeline.log")
lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
today = "2026-06-15"
today_lines = [l for l in lines if l.startswith(f"[{today}")]

# 今日の統計
registered = [l for l in today_lines if "[OK] 案件登録" in l]
skipped = [l for l in today_lines if "[SKIP]" in l or "スキップ" in l]
duplicate = [l for l in today_lines if "重複" in l or "duplicate" in l.lower() or "既存" in l]
errors = [l for l in today_lines if "[NG]" in l or "ERROR" in l or "失敗" in l]

print(f"=== mail_pipeline 本日({today})の案件処理統計 ===")
print(f"案件登録成功: {len(registered)}件")
print(f"スキップ: {len(skipped)}件")
print(f"重複/既存: {len(duplicate)}件")
print(f"エラー/失敗: {len(errors)}件")
print(f"合計ログ行数: {len(today_lines)}行")

print("\nスキップ理由（上位5件）:")
for l in skipped[:5]:
    print(f"  {l[:100]}")

print("\nエラー例（上位5件）:")
for l in errors[:5]:
    print(f"  {l[:100]}")

# LNGのログから案件分類の詳細
ng_lines = [l for l in today_lines if "[NG]" in l]
print(f"\n[NG]件数: {len(ng_lines)}件")
for l in ng_lines[:5]:
    print(f"  {l[:100]}")
