"""8.4 SPEC §6 統一実行順序の検証（モデル選択→閾値→dedup→reserve→budget）。"""

from __future__ import annotations


def _mock_all(monkeypatch, fail_at: str | None = None):
    """allowed() 内の各ステップをモックして実行順序を検証するヘルパ。"""
    call_order = []

    from common.model_selector import ModelSelection

    def mock_select(p, model_hint=None):
        call_order.append("select_model")
        if fail_at == "select_model":
            from common.model_selector import ModelSelectionError

            raise ModelSelectionError("error_transient_models_list")
        return ModelSelection("gpt-4o-mini", "light", False, False)

    monkeypatch.setattr("common.model_selector.select_model", mock_select)

    original_validate = None
    try:
        import common.dedup as _d

        original_validate = _d.validate_target_id

        def mock_validate(block_type, target_id):
            call_order.append("validate_target_id")
            if fail_at == "validate_target_id":
                raise ValueError(f"target_id required for block_type={block_type}")
            if original_validate:
                original_validate(block_type, target_id)

        monkeypatch.setattr("common.dedup.validate_target_id", mock_validate)
    except Exception:
        pass

    return call_order


def test_model_fails_before_threshold(monkeypatch):
    """Step1 のモデル選択失敗は Step2 以降を実行しない。"""
    from common.model_selector import ModelSelectionError

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: (_ for _ in ()).throw(ModelSelectionError("error_transient_models_list")),
    )
    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="manual_query", script="test")
    assert d.reason == cg.Reasons.error_transient_models_list
    assert d.exit_code == 2


def test_threshold_fails_before_dedup(monkeypatch):
    """Step3 閾値超過は Step5 claim_dedup を実行しない。"""
    from common.model_selector import ModelSelection

    monkeypatch.setenv("PHASE_THRESHOLD_LIGHT", "0.000001")
    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    claim_called = []
    monkeypatch.setattr("common.dedup.claim_dedup", lambda k, ttl_sec=3600: claim_called.append(k) or "x")

    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="manual_query", est_in=10000, est_out=10000, script="test")
    assert d.reason == cg.Reasons.stopped_phase_threshold
    assert len(claim_called) == 0, "claim_dedup should not be called when threshold exceeded"


def test_duplicate_before_reserve(monkeypatch):
    """Step5 重複 claim は Step6 reserve を実行しない。"""
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    monkeypatch.setattr("common.dedup.claim_dedup", lambda k, ttl_sec=3600: None)

    reserve_called = []
    monkeypatch.setattr("common.ledger.reserve", lambda p: reserve_called.append(p) or "rid")

    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="manual_query", script="test")
    assert d.reason == cg.Reasons.skipped_duplicate
    assert len(reserve_called) == 0, "reserve should not be called when duplicate"
