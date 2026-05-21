"""freee_invoice_v2 ドライラン確認（API送信なし）"""
import sys
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee")

from token_manager import get_headers
from freee_invoice_v2 import load_active_entries
from datetime import date
from dateutil.relativedelta import relativedelta

# トークン確認
h = get_headers()
print(f"[TOKEN] OK: {list(h.keys())}")

# Excel読み込み確認
entries = load_active_entries()
print(f"\n[EXCEL] 対象人員: {len(entries)}名")
total = 0
for e in entries:
    print(f"  {e['source']} | {e['name']} | 粗利{e['profit']:,}円 | 請求{e['seikyu']:,}円")
    total += e['seikyu']
print(f"\n[合計請求額] {total:,}円")

# 次月の請求日・支払期限
today = date.today()
target = (today.replace(day=1) + relativedelta(months=1))
issue_date = target.replace(day=1)
due_date = issue_date + relativedelta(months=1) - relativedelta(days=1)
print(f"\n[日付] 請求日: {issue_date} / 支払期限: {due_date}")
print("\n✅ ドライラン完了 - 問題なし")
