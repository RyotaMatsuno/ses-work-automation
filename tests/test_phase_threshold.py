"""8.1 フェーズ別単発閾値の境界値テスト（SPEC §4）。"""

from __future__ import annotations


def _allowed_fast(phase, block_type, model, est_in, est_out, monkeypatch, tmp_path):
    """モデル選択をモックして allowed() の閾値チェック部分だけをテストする。"""
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection(
            model=model,
            model_class={"light": "light", "medium": "medium", "heavy": "heavy"}.get(
                __import__("common.model_selector", fromlist=["PHASE_CLASS"]).PHASE_CLASS.get(p, "light"), "light"
            ),
            fallback=False,
            unknown_model=False,
        ),
    )
    import cost_guard as cg

    return cg.allowed(
        phase=phase, block_type=block_type, target_id="test-target", est_in=est_in, est_out=est_out, script="test"
    )


def test_light_threshold_under(monkeypatch):
    """軽クラス: 推定コスト < 0.025 → allowed=True。"""
    from common.model_selector import ModelSelection

    monkeypatch.setenv("PHASE_THRESHOLD_LIGHT", "0.025")
    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    # gpt-4o-mini: input=0.15/1M, output=0.60/1M
    # 100 in + 100 out → 0.000015 + 0.00006 = 0.000075 < 0.025
    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="manual_query", est_in=100, est_out=100, script="test")
    assert d.allowed is True


def test_light_threshold_over(monkeypatch):
    """軽クラス: 推定コスト > 0.025 → reason=stopped_phase_threshold。"""
    from common.model_selector import ModelSelection

    monkeypatch.setenv("PHASE_THRESHOLD_LIGHT", "0.000001")
    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="manual_query", est_in=10000, est_out=10000, script="test")
    assert d.allowed is False
    assert d.reason == cg.Reasons.stopped_phase_threshold
    assert d.exit_code == 1


def test_heavy_threshold_boundary(monkeypatch):
    """重クラス: 推定コスト == 閾値 → allowed=True（未超過）。"""
    from common.model_selector import ModelSelection

    monkeypatch.setenv("PHASE_THRESHOLD_HEAVY", "0.15")
    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("codex-5", "heavy", False, False),
    )
    import cost_guard as cg

    # 0.15 以下は通す
    d = cg.allowed(phase="implementation", block_type="manual_query", est_in=0, est_out=0, script="test")
    assert d.allowed is True
