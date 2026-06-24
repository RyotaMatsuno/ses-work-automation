from datetime import date

from common.sheet_dates import parse_contract_dates, parse_kikan_end, parse_sheet_date


def test_parse_sheet_date_year_month():
    assert parse_sheet_date("2023/12") == date(2023, 12, 1)
    assert parse_sheet_date("2024/3") == date(2024, 3, 1)


def test_parse_kikan_end_patterns():
    start = date(2026, 3, 1)
    assert parse_kikan_end("長期", start) is None
    assert parse_kikan_end("5月末終了", start) == date(2026, 5, 31)
    assert parse_kikan_end("2025/3退場", start) == date(2025, 3, 31)


def test_parse_contract_dates_from_sankaku_kikan():
    row = ["", "", "", "田中", "2024/5", "長期"] + [""] * 10
    start, end = parse_contract_dates(
        row,
        start_col=None,
        end_col=None,
        sankaku_col=4,
        kikan_col=5,
    )
    assert start == date(2024, 5, 1)
    assert end is None
