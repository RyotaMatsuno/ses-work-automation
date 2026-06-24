"""8.13b claim_dedup 内で期限切れ未確定 claim を inline purge するテスト（SPEC §5.3）。"""

from __future__ import annotations

import time

from common.dedup import claim_dedup
from common.state_store import init_schema, open_conn


def test_inline_purge_of_expired_unconfirmed_claim():
    """TTL=0 秒に設定した未確定 claim は次回 claim_dedup 時に purge される。"""
    init_schema()
    key = "2026-06-17:skill_judge:research:ttl-purge-001"

    # TTL=0 で claim（即時期限切れ）
    claim_id = claim_dedup(key, ttl_sec=0)
    assert claim_id is not None

    # レコードが存在する（まだ purge されていない）
    conn = open_conn()
    try:
        row = conn.execute("SELECT * FROM dedup_claims WHERE claim_id=?", (claim_id,)).fetchone()
        assert row is not None
    finally:
        conn.close()

    # 少し待って次の claim を呼ぶ → inline purge が走る
    time.sleep(0.01)
    new_claim_id = claim_dedup(key, ttl_sec=3600)

    # purge 後に再 claim できた
    assert new_claim_id is not None
    assert new_claim_id != claim_id

    # 古い未確定レコードは purge されている
    conn = open_conn()
    try:
        old_row = conn.execute("SELECT * FROM dedup_claims WHERE claim_id=?", (claim_id,)).fetchone()
        assert old_row is None, "Expired unconfirmed claim should have been purged"
    finally:
        conn.close()


def test_confirmed_claim_not_purged_by_inline():
    """inline purge は confirmed=0 のみを対象とする（confirmed=1 は保護）。"""
    init_schema()
    key = "2026-06-17:skill_judge:research:ttl-confirm-001"
    claim_id = claim_dedup(key, ttl_sec=0)
    assert claim_id is not None

    # confirm する
    from common.dedup import confirm_dedup

    confirm_dedup(claim_id)

    # 次の claim で inline purge が走っても confirmed=1 は消えない
    another = claim_dedup("different-key-xyz", ttl_sec=0)

    conn = open_conn()
    try:
        row = conn.execute("SELECT confirmed FROM dedup_claims WHERE claim_id=?", (claim_id,)).fetchone()
        assert row is not None, "Confirmed claim should NOT be purged"
        assert row["confirmed"] == 1
    finally:
        conn.close()
