"""8.11 transient 失敗で release_dedup → 再 claim 可能（SPEC §5.2 / v2.10.1）。"""

from __future__ import annotations

from common.dedup import claim_dedup, confirm_dedup, release_dedup
from common.state_store import init_schema, open_conn


def test_transient_release_allows_reclaim():
    """transient 失敗時は release_dedup が error=2 マーカーをセットし、再 claim できる。"""
    key = "2026-06-17:skill_judge:research:transient-001"

    claim_id = claim_dedup(key)
    assert claim_id is not None

    release_dedup(claim_id)

    init_schema()
    conn = open_conn()
    try:
        row = conn.execute(
            "SELECT confirmed, error FROM dedup_claims WHERE claim_id=?",
            (claim_id,),
        ).fetchone()
        assert row is not None
        assert row["confirmed"] == 1
        assert row["error"] == 2
    finally:
        conn.close()

    new_id = claim_dedup(key)
    assert new_id is not None
    assert new_id != claim_id
    confirm_dedup(new_id)


def test_confirmed_claim_cannot_be_reclaimed():
    """success 後の confirm_dedup は UNIQUE を維持するので再 claim 不可。"""
    key = "2026-06-17:skill_judge:research:confirmed-001"
    claim_id = claim_dedup(key)
    assert claim_id is not None
    confirm_dedup(claim_id)

    again = claim_dedup(key)
    assert again is None


def test_permanent_error_confirm_prevents_reclaim():
    """permanent 失敗の confirm_dedup(error=True) も UNIQUE を維持する。"""
    key = "2026-06-17:skill_judge:research:perm-error-001"
    claim_id = claim_dedup(key)
    assert claim_id is not None
    confirm_dedup(claim_id, error=True)

    again = claim_dedup(key)
    assert again is None
