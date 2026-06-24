import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from datetime import date, timedelta


def is_active_in_month(start: date, end: date | None, target_month: str) -> bool:
    """
    start: 契約開始日（必須）
    end: 契約終了日（None = セル空欄 = 継続中）
    target_month: "YYYY-MM"
    """
    year, month = map(int, target_month.split("-"))
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year, 12, 31)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    if start > last_day:
        return False
    if end is not None and end < first_day:
        return False
    return True
