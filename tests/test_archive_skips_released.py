"""8.31 archive cron が error=2(released) をスキップ（SPEC v2.10.1 §3.3）。"""

from __future__ import annotations

from common.dedup import archive_confirmed_dedup_claims, claim_dedup, confirm_dedup, release_dedup
from common.state_store import init_schema, open_conn


def test_archive_skips_released():
    success_key = "2026-06-17:skill_judge:research:arch-success-001"
    released_key = "2026-06-17:skill_judge:research:arch-released-001"

    success_id = claim_dedup(success_key)
    released_id = claim_dedup(released_key)
    assert success_id and released_id

    confirm_dedup(success_id, error=False)
    release_dedup(released_id)

    archived = archive_confirmed_dedup_claims()
    assert archived == 1

    init_schema()
    conn = open_conn()
    try:
        success_row = conn.execute(
            "SELECT claim_id FROM dedup_claims WHERE claim_id=?",
            (success_id,),
        ).fetchone()
        released_row = conn.execute(
            "SELECT confirmed, error FROM dedup_claims WHERE claim_id=?",
            (released_id,),
        ).fetchone()
        archive_success = conn.execute(
            "SELECT claim_id FROM dedup_claims_archive WHERE claim_id=?",
            (success_id,),
        ).fetchone()

        assert success_row is None
        assert archive_success is not None
        assert released_row is not None
        assert released_row["error"] == 2
    finally:
        conn.close()
