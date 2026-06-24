"""8.14 permanent_auth / bad_request / response_invalid / api の finalize テスト。"""

from __future__ import annotations

import pytest

import cost_guard as cg


def _make_allowed(monkeypatch, target_id="proj-perm-001"):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    d = cg.allowed(phase="research", block_type="skill_judge", target_id=target_id, script="test")
    assert d.allowed is True
    return d


@pytest.mark.parametrize(
    "error_kind,expected_reason",
    [
        ("permanent_auth", "error_auth"),
        ("permanent_bad_request", "error_bad_request"),
        ("permanent_response_invalid", "error_response_invalid"),
        ("permanent_api", "error_permanent_api"),
    ],
)
def test_permanent_kinds_do_not_raise(monkeypatch, error_kind, expected_reason):
    """各 permanent error_kind で finalize が OK_RECORDED を返す。"""
    d = _make_allowed(monkeypatch, target_id=f"proj-{error_kind}")
    result = cg.finalize(d, in_tokens=100, out_tokens=50, success=False, error_kind=error_kind)
    assert result.status == cg.FinalizeStatus.OK_RECORDED


@pytest.mark.parametrize(
    "error_kind", ["permanent_auth", "permanent_bad_request", "permanent_response_invalid", "permanent_api"]
)
def test_permanent_fails_confirm_dedup(monkeypatch, error_kind):
    """permanent 失敗後は confirm_dedup(error=True) → UNIQUE 維持 → 再 claim 不可。"""
    from common.dedup import claim_dedup

    d = _make_allowed(monkeypatch, target_id=f"proj-perm-recheck-{error_kind}")
    assert d.claim_id is not None

    cg.finalize(d, success=False, error_kind=error_kind)

    again = claim_dedup(d.dedup_key)
    assert again is None
