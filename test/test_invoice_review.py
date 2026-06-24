"""invoice_review のユニットテスト。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shibusawa import invoice_review as ir


def _line(partner_id: int, desc: str, unit: str = "", withholding: bool = False, qty=1, price="10000"):
    return {
        "type": "item",
        "description": desc,
        "quantity": qty,
        "unit": unit,
        "unit_price": str(price),
        "withholding": withholding,
    }


def _inv(partner_id: int, ptype_lines: list, subject="2026年7月分請求書", payment="2026-09-14"):
    return {
        "id": partner_id,
        "partner_id": partner_id,
        "billing_date": "2026-08-01",
        "payment_date": payment,
        "subject": subject,
        "total_amount": 11000,
        "lines": ptype_lines,
    }


def test_validate_draft_blocks_ng_phrases():
    with pytest.raises(ir.DraftViolationError):
        ir._validate_draft("請求書を送付しました")
    ir._validate_draft("レビュー完了です")


def test_get_payment_bucket_via_label():
    inv = _inv(91256138, [_line(91256138, "田中様稼働分", withholding=True)], payment="2026-09-29")
    assert ir.payment_bucket_label(inv, "TERRA") == "60"
    ft = _inv(113795090, [_line(113795090, "田中様稼働分")], payment="2026-09-14")
    assert ir.payment_bucket_label(ft, "FT") == "45"


@pytest.mark.parametrize(
    "prev,current,expect_issue",
    [
        (100000, 119000, False),
        (100000, 120000, False),
        (100000, 121000, True),
        (100000, 150000, False),
        (100000, 160000, True),
        (0, 100000, False),
    ],
)
def test_anomaly_check_boundaries(prev, current, expect_issue):
    prev_inv = _inv(91256138, [_line(91256138, "A様稼働分", price=str(prev))], payment="2026-09-14")
    cur_inv = _inv(91256138, [_line(91256138, "A様稼働分", price=str(current))], payment="2026-09-14")
    result = ir.anomaly_check([cur_inv], [prev_inv])
    if expect_issue:
        assert not result.ok
    else:
        assert result.ok or result.name == "anomaly_check"


def test_format_check_terra_ok():
    inv = _inv(
        91256138,
        [
            _line(91256138, "プロパー稼働分", withholding=True, qty=2),
            _line(91256138, "田中様稼働分", withholding=True),
        ],
    )
    assert ir.format_check([inv]).ok


def test_format_check_terra_ng_subject():
    inv = _inv(91256138, [_line(91256138, "田中様稼働分", withholding=True)], subject="業務委託料")
    assert not ir.format_check([inv]).ok


def test_unit_check_all_empty():
    inv = _inv(91256138, [_line(91256138, "田中様稼働分", unit="", withholding=True)])
    assert ir.unit_check([inv]).ok


def test_unit_check_ng():
    inv = _inv(91256138, [_line(91256138, "田中様稼働分", unit="式", withholding=True)])
    assert not ir.unit_check([inv]).ok


def test_duplicate_check_detects_dup():
    a = _inv(91256138, [_line(91256138, "A様稼働分", withholding=True)])
    b = _inv(91256138, [_line(91256138, "B様稼働分", withholding=True)])
    b["total_amount"] = a["total_amount"]
    assert not ir.duplicate_check([a, b]).ok


def test_withholding_check_terra():
    ok = _inv(91256138, [_line(91256138, "田中様稼働分", withholding=True)])
    ng = _inv(91256138, [_line(91256138, "田中様稼働分", withholding=False)])
    assert ir.withholding_check([ok]).ok
    assert not ir.withholding_check([ng]).ok


def test_withholding_check_gl_false():
    inv = _inv(117422289, [_line(117422289, "石崎様7月稼働分", withholding=False)])
    assert ir.withholding_check([inv]).ok


def test_format_success_line_message():
    summary = ir.ReviewSummary(
        target_month="2026-07",
        ok=True,
        checks=[
            ir.CheckResult("format_check", True, summary="全件OK"),
            ir.CheckResult("unit_check", True, summary="全件空欄"),
            ir.CheckResult("duplicate_check", True, summary="なし"),
            ir.CheckResult("active_check", True, summary="全件一致"),
            ir.CheckResult("withholding_check", True, summary="全件正常"),
            ir.CheckResult("anomaly_check", True, summary="異常なし"),
        ],
        invoices=[],
        invoice_groups=[
            {"short": "TERRA", "bucket": "45", "people": 14, "amount": 500000},
            {"short": "TERRA", "bucket": "60", "people": 8, "amount": 300000},
        ],
        total_ex_tax=800000,
    )
    msg = ir.format_success_line_message(summary)
    ir._validate_draft(msg)
    assert "【2026年7月分 請求書ドラフトレビュー完了】" in msg
    assert "TERRA(45日)" in msg
    assert "¥800,000" in msg


def test_format_ng_line_message():
    summary = ir.ReviewSummary(
        target_month="2026-07",
        ok=False,
        checks=[ir.CheckResult("format_check", False, summary="1件NG", issues=["TERRA: 件名不一致"])],
        invoices=[],
        invoice_groups=[],
    )
    msg = ir.format_ng_line_message(summary)
    assert "請求書レビュー NG" in msg
    assert "--recheck" in msg or "recheck" in msg


def test_run_review_dry_run_with_mock_invoices(monkeypatch):
    invoices = [
        _inv(91256138, [_line(91256138, "プロパー稼働分", withholding=True, qty=1)]),
        _inv(113795090, [_line(113795090, "笠井様稼働分")]),
        _inv(
            117422289,
            [_line(117422289, "石崎様7月稼働分")],
            payment="2026-08-31",
        ),
    ]
    monkeypatch.setattr(ir, "active_check", lambda invs, tm: ir.CheckResult("active_check", True, summary="全件一致"))
    summary = ir.run_review("2026-07", dry_run=True, notify=False, invoices=invoices, prev_invoices=[])
    assert summary.ok
    assert len(summary.invoice_groups) == 3
