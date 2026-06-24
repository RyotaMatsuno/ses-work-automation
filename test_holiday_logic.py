import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# should_run_today()のロジックを単体テスト
sys.path.insert(0, r"freee")
# 直接関数だけロードしてテスト
from datetime import date, timedelta

import jpholiday as _jpholiday


def _is_business_day(d):
    return d.weekday() < 5 and not _jpholiday.is_holiday(d)


def _next_business_day(d):
    while not _is_business_day(d):
        d += timedelta(days=1)
    return d


# 6月のテスト（6/15は日曜 → 翌営業日=6/16月曜）
year, month = 2026, 6
last_day = date(year, month + 1, 1) - timedelta(days=1)
mid = date(year, month, 15)

mid_biz = _next_business_day(mid)
eom_biz = _next_business_day(last_day)

print("2026年6月")
print(f"  15日({mid.strftime('%a')}) → 翌営業日: {mid_biz} ({mid_biz.strftime('%a')})")
print(f"  月末={last_day}({last_day.strftime('%a')}) → 翌営業日: {eom_biz} ({eom_biz.strftime('%a')})")

# 今日（2026-05-25 月曜）はどちらでもないのでskipされるはず
today = date.today()
target_year, target_month = today.year, today.month
if target_month == 12:
    tl = date(target_year + 1, 1, 1) - timedelta(days=1)
else:
    tl = date(target_year, target_month + 1, 1) - timedelta(days=1)
targets = [_next_business_day(date(target_year, target_month, 15)), _next_business_day(tl)]
print(f"\n今月({target_month}月)のチェック日: {targets}")
print(f"今日({today})は実行対象: {today in targets}")
