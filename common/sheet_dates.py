"""契約マスターSheetの日付セル解析。"""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime


def _last_day_of_month(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def parse_sheet_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    if not s or s in ("-", "―", "ー"):
        return None

    m = re.match(r"^(\d{4})[/.-](\d{1,2})$", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), 1)

    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d", "%Y年%m月%d日", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    m = re.match(r"(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def parse_kikan_end(kikan: str, start: date | None) -> date | None:
    text = str(kikan or "").strip()
    if not text or text in ("長期", "-", "―"):
        return None

    m = re.search(r"(\d{4})[/.-](\d{1,2})", text)
    if m and any(k in text for k in ("退場", "終了", "まで")):
        return _last_day_of_month(int(m.group(1)), int(m.group(2)))

    m = re.match(r"(\d{1,2})月末終了", text)
    if m:
        month = int(m.group(1))
        year = start.year if start else date.today().year
        if start and month < start.month:
            year += 1
        return _last_day_of_month(year, month)

    return None


def parse_contract_dates(
    row: list[str],
    *,
    start_col: int | None,
    end_col: int | None,
    sankaku_col: int | None = None,
    kikan_col: int | None = None,
) -> tuple[date | None, date | None]:
    start = None
    end = None
    if start_col is not None and start_col < len(row):
        start = parse_sheet_date(row[start_col])
    if end_col is not None and end_col < len(row):
        end = parse_sheet_date(row[end_col])
    if start is None and sankaku_col is not None and sankaku_col < len(row):
        start = parse_sheet_date(row[sankaku_col])
    if kikan_col is not None and kikan_col < len(row):
        kikan = row[kikan_col]
        if end is None:
            end = parse_kikan_end(kikan, start)
        if start is None and kikan:
            parts = re.split(r"[~～\-ー―]", str(kikan))
            if parts[0].strip():
                start = parse_sheet_date(parts[0])
    return start, end
