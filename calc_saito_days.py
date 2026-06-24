# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
from datetime import date, timedelta

# 2026年5月の営業日計算
# 祝日: 5/3(憲法記念日) 5/4(みどりの日) 5/5(こどもの日) 5/6(振替休日)
holidays_may = {date(2026, 5, 3), date(2026, 5, 4), date(2026, 5, 5), date(2026, 5, 6)}

# 5月の全営業日
all_busdays = []
d = date(2026, 5, 1)
while d.month == 5:
    if d.weekday() < 5 and d not in holidays_may:
        all_busdays.append(d)
    d += timedelta(days=1)

print(f"5月営業日数: {len(all_busdays)}日", flush=True)
print(f"営業日一覧: {[str(x) for x in all_busdays]}", flush=True)

# 5/15以降の営業日
from_may15 = [x for x in all_busdays if x >= date(2026, 5, 15)]
print(f"\n5/15以降の営業日数: {len(from_may15)}日", flush=True)
print(f"5/15以降: {[str(x) for x in from_may15]}", flush=True)

# 日割り計算（ベースは18営業日）
base_days = 18  # 発注書記載のベース日数
unit_price = 430000
day_rate = unit_price / base_days
billing_days = len(from_may15)
billing_amount = day_rate * billing_days

ningetsu = billing_days / base_days

print("\n=== 齋藤よしまさ 5月日割り計算 ===", flush=True)
print(f"ベース日数: {base_days}営業日", flush=True)
print(f"1日単価: {unit_price:,}÷{base_days} = {day_rate:,.0f}円/日", flush=True)
print(f"5/15〜5/31稼働日数: {billing_days}日", flush=True)
print(f"請求額: {day_rate:,.0f}×{billing_days}日 = {billing_amount:,.0f}円", flush=True)
print(f"人月換算: {billing_days}/{base_days} = {ningetsu:.3f}人月", flush=True)
