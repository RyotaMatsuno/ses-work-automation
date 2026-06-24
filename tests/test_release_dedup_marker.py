"""8.30 release_dedup が confirmed=1/error=2 マーカーで完了表現（SPEC v2.10.1 §3.1）。"""

from __future__ import annotations

from common.dedup import claim_dedup, release_dedup
from common.state_store import init_schema, open_conn


def test_release_dedup_marker():
    key = "2026-06-17:skill_judge:research:marker-001"
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
