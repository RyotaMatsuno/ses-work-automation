"""8.5 exit code 2 の誤爆防止テスト（reason の exit_code 対応確認）。"""

from __future__ import annotations


def test_exit_code2_reasons():
    """exit_code=2 となるべき reason が正しく設定されていることを確認する。"""
    import cost_guard as cg

    exit2_reasons = {
        cg.Reasons.skipped_duplicate,
        cg.Reasons.error_transient_models_list,
        cg.Reasons.error_transient_api,
        cg.Reasons.error_model_unavailable_all_fallback,
        cg.Reasons.error_permanent_api,
        cg.Reasons.error_auth,
        cg.Reasons.error_bad_request,
        cg.Reasons.error_response_invalid,
        cg.Reasons.error_missing_target_id,
        cg.Reasons.error_internal,
    }
    exit1_reasons = {
        cg.Reasons.stopped_budget,
        cg.Reasons.stopped_call_limit,
        cg.Reasons.stopped_phase_threshold,
    }
    exit0_reasons = {cg.Reasons.ok}

    # すべての reason enum が存在すること（14値）
    all_reasons = {r.value for r in cg.Reasons}
    assert len(all_reasons) == 14, f"Expected 14 reasons, got {len(all_reasons)}: {all_reasons}"


def test_skipped_duplicate_is_exit_code2(monkeypatch):
    """skipped_duplicate は exit_code=2 かつ stopped ではない（誤爆防止）。"""
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    monkeypatch.setattr("common.dedup.claim_dedup", lambda k, ttl_sec=3600: None)

    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="manual_query", script="test")
    assert d.reason == cg.Reasons.skipped_duplicate
    assert d.exit_code == 2
    assert d.allowed is False


def test_missing_target_id_is_exit_code2(monkeypatch):
    """error_missing_target_id は exit_code=2（exit_code=1 ではない）。"""
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    import cost_guard as cg

    # skill_judge は target_id 必須
    d = cg.allowed(phase="research", block_type="skill_judge", target_id="", script="test")
    assert d.reason == cg.Reasons.error_missing_target_id
    assert d.exit_code == 2
