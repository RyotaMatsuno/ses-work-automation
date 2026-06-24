"""8.13c claim → finalize なし → TTL 経過 → 再 claim 成功（SPEC §5.3）。"""

from __future__ import annotations

import time

from common.dedup import claim_dedup
from common.state_store import init_schema


def test_expired_claim_can_be_reclaimed():
    """finalize しない claim が TTL=0 で期限切れになった後、再 claim できる。"""
    init_schema()
    key = "2026-06-17:skill_judge:research:expire-reclaim-001"

    # TTL=0 の claim（即時期限切れ、finalize は呼ばない）
    claim_id = claim_dedup(key, ttl_sec=0)
    assert claim_id is not None

    # TTL 経過を模擬（実際には time.sleep(0) + 次の call での purge で十分）
    time.sleep(0.01)

    # 再 claim を試みる → inline purge が走り成功する
    new_id = claim_dedup(key, ttl_sec=3600)
    assert new_id is not None, "Should be able to re-claim after TTL expiry"
    assert new_id != claim_id


def test_non_expired_claim_blocks_reclaim():
    """TTL 未経過の claim は再 claim をブロックする。"""
    init_schema()
    key = "2026-06-17:skill_judge:research:non-expire-001"

    claim_id = claim_dedup(key, ttl_sec=3600)
    assert claim_id is not None

    # すぐに再 claim → ブロックされる
    again = claim_dedup(key, ttl_sec=3600)
    assert again is None
