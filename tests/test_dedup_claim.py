"""8.2 claim 方式の INSERT 検証（SPEC §5.2）。"""

from __future__ import annotations

from common.dedup import claim_dedup, confirm_dedup, release_dedup


def test_first_claim_succeeds():
    """同一 dedup_key の最初の claim は成功する。"""
    claim_id = claim_dedup("2026-06-17:skill_judge:research:proj-001")
    assert claim_id is not None
    assert isinstance(claim_id, str)


def test_duplicate_claim_returns_none():
    """同じ dedup_key の2回目 claim は None を返す（UNIQUE 違反）。"""
    key = "2026-06-17:skill_judge:research:proj-002"
    claim_id1 = claim_dedup(key)
    assert claim_id1 is not None
    claim_id2 = claim_dedup(key)
    assert claim_id2 is None


def test_claim_different_keys():
    """異なる dedup_key は両方 claim できる。"""
    id1 = claim_dedup("2026-06-17:skill_judge:research:proj-003")
    id2 = claim_dedup("2026-06-17:skill_judge:research:proj-004")
    assert id1 is not None
    assert id2 is not None
    assert id1 != id2


def test_confirm_dedup_marks_confirmed():
    """confirm_dedup 後に同一 key は再 claim できない（confirmed=1 は UNIQUE 維持）。"""
    key = "2026-06-17:skill_judge:research:proj-005"
    claim_id = claim_dedup(key)
    assert claim_id is not None
    confirm_dedup(claim_id)
    # confirmed=1 のレコードは inline purge されないので再 claim は失敗する
    again = claim_dedup(key)
    assert again is None


def test_release_allows_reclaim():
    """release_dedup 後は同一 key を再 claim できる。"""
    key = "2026-06-17:skill_judge:research:proj-006"
    claim_id = claim_dedup(key)
    assert claim_id is not None
    release_dedup(claim_id)
    new_id = claim_dedup(key)
    assert new_id is not None
    assert new_id != claim_id
