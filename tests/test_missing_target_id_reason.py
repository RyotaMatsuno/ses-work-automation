"""8.13 target_id 必須 block_type で未指定 → reason=error_missing_target_id（SPEC §5.4）。"""

from __future__ import annotations


def _mock_select(monkeypatch):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )


def test_required_block_type_missing_target_id(monkeypatch):
    """skill_judge は target_id 必須。空文字で呼ぶと error_missing_target_id。"""
    _mock_select(monkeypatch)
    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="skill_judge", target_id="", script="test")
    assert d.allowed is False
    assert d.reason == cg.Reasons.error_missing_target_id
    assert d.exit_code == 2


def test_optional_block_type_missing_target_id(monkeypatch):
    """manual_query は target_id 任意。空文字でも allowed になる。"""
    _mock_select(monkeypatch)
    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="manual_query", target_id="", script="test")
    # budget / call_limit に引っかからなければ allowed になる
    assert d.reason != cg.Reasons.error_missing_target_id


def test_required_block_type_with_target_id_passes(monkeypatch):
    """skill_judge に target_id を指定すれば error_missing_target_id にならない。"""
    _mock_select(monkeypatch)
    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="skill_judge", target_id="proj-12345", script="test")
    assert d.reason != cg.Reasons.error_missing_target_id


def test_gate_check_requires_target_id(monkeypatch):
    """gate_check も target_id 必須。"""
    _mock_select(monkeypatch)
    import cost_guard as cg

    d = cg.allowed(phase="design", block_type="gate_check", target_id="", script="test")
    assert d.reason == cg.Reasons.error_missing_target_id
