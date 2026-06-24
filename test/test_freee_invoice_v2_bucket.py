import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "freee"))
sys.path.insert(0, str(ROOT))

from freee_invoice_v2 import get_payment_bucket

import sheets_reader as SR


@pytest.mark.parametrize(
    "site_days,source,expected",
    [
        (30, "TERRA", "30"),
        (45, "TERRA", "45"),
        (46, "TERRA", "60"),
        (60, "TERRA", "60"),
        (61, "TERRA", "60"),
        (60, "GL", "60"),
        (100, "FT", "45"),
    ],
)
def test_get_payment_bucket(site_days, source, expected):
    assert get_payment_bucket(site_days, source) == expected


@pytest.mark.parametrize(
    "case,expected",
    [
        ("フラップテック上位", True),
        ("グレイスライン経由", True),
        ("GL案件", True),
        ("FT", True),
        ("自社直案件", False),
    ],
)
def test_is_gl_ft(case, expected):
    assert SR._is_gl_ft(case) is expected


def test_terra_empty_site_gl_ft_goes_to_excluded_list():
    terra_row = [""] * 21
    terra_row[0] = ""
    terra_row[1] = "P"
    terra_row[2] = "稼働中"
    terra_row[3] = "川崎(新)"
    terra_row[4] = "2026/4"
    terra_row[5] = "長期"
    terra_row[6] = "（調整中）"
    terra_row[7] = "500000"
    terra_row[13] = "400000"
    ft_row = ["", "稼働中", "川崎健太"] + [""] * 10

    sheets = {
        "TERRA": [
            ["h1"],
            ["h2"],
            ["h3"],
            ["担当", "区分", "ステータス", "氏名", "参画時期", "期間", "案件/上位会社", "単価(案件)", "支払サイト"],
            terra_row,
        ],
        "フラップテック": [[], [], ["担当", "ステータス", "氏名"], ft_row],
        "グレイスライン": [[], [], ["ステータス", "氏名"]],
    }

    with patch.object(SR, "_open") as mock_open, patch.object(SR, "_notify_line") as notify:
        ss = MagicMock()
        mock_open.return_value = ss

        def worksheet(name):
            ws = MagicMock()
            ws.get_all_values.return_value = sheets[name]
            return ws

        ss.worksheet.side_effect = worksheet
        entries, meta = SR.load_active_entries(target_month=date(2026, 7, 1))

    assert "TERRA/川崎(新)" in meta["excluded_gl_ft_props"]
    assert not any("川崎" in s for s in meta["skipped_other"])
    notify.assert_not_called()
    assert len(entries) == 0


def test_terra_empty_site_non_gl_ft_warns():
    terra_row = [""] * 21
    terra_row[1] = "P"
    terra_row[2] = "稼働中"
    terra_row[3] = "テスト太郎"
    terra_row[4] = "2026/4"
    terra_row[5] = "長期"
    terra_row[6] = "自社案件"
    terra_row[7] = "500000"
    terra_row[13] = "400000"

    sheets = {
        "TERRA": [
            ["h1"],
            ["h2"],
            ["h3"],
            ["担当", "区分", "ステータス", "氏名", "参画時期", "期間", "案件/上位会社", "単価(案件)", "支払サイト"],
            terra_row,
        ],
        "フラップテック": [[], [], ["担当"]],
        "グレイスライン": [[], [], ["ステータス"]],
    }

    with patch.object(SR, "_open") as mock_open, patch.object(SR, "_notify_line") as notify:
        ss = MagicMock()
        mock_open.return_value = ss

        def worksheet(name):
            ws = MagicMock()
            ws.get_all_values.return_value = sheets[name]
            return ws

        ss.worksheet.side_effect = worksheet
        entries, meta = SR.load_active_entries(target_month=date(2026, 7, 1))

    assert any("テスト太郎" in s and "支払サイト未入力" in s for s in meta["skipped_other"])
    assert meta["site_missing_warnings"]
    notify.assert_called_once()
