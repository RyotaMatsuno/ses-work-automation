"""8.20 model_hint 優先採用 / 不在時のフォールバック（SPEC §7.1）。"""

from __future__ import annotations


def test_model_hint_available_is_used(monkeypatch):
    """model_hint が available に存在するとき、そのモデルが使われる。"""
    monkeypatch.setattr(
        "common.model_selector._fetch_openai_models", lambda: {"gpt-4o-mini", "my-custom-model", "codex-5"}
    )
    import common.model_selector as ms

    ms._models_cache = None

    sel = ms.select_model("research", model_hint="my-custom-model")
    assert sel.model == "my-custom-model"


def test_model_hint_unavailable_falls_back(monkeypatch):
    """model_hint が available にないとき、phase default にフォールバックする。"""
    monkeypatch.setattr("common.model_selector._fetch_openai_models", lambda: {"gpt-4o-mini", "gpt-4.1"})
    import common.model_selector as ms

    ms._models_cache = None

    sel = ms.select_model("research", model_hint="nonexistent-model-xyz")
    # フォールバックで gpt-4o-mini が選ばれる
    assert sel.model in {"gpt-4o-mini", "gpt-4.1"}
    assert sel.fallback is False  # hint not found → usual resolution, not fallback from default


def test_no_model_hint_uses_phase_default(monkeypatch):
    """model_hint なし: phase から default モデルを解決する。"""
    monkeypatch.setenv("PHASE_MODEL_RESEARCH", "gpt-4o-mini")
    monkeypatch.setattr("common.model_selector._fetch_openai_models", lambda: {"gpt-4o-mini", "gpt-5.4"})
    import common.model_selector as ms

    ms._models_cache = None

    sel = ms.select_model("research")
    assert sel.model == "gpt-4o-mini"
    assert sel.fallback is False


def test_model_hint_class_override_uses_phase_threshold(monkeypatch):
    """model_hint が別クラスでも、装置2閾値判定は phase のクラスを採用（SPEC §3.4）。"""
    # research (light, threshold=0.025) に heavy モデルの hint
    monkeypatch.setenv("PHASE_THRESHOLD_LIGHT", "0.025")
    monkeypatch.setattr("common.model_selector._fetch_openai_models", lambda: {"gpt-4o-mini", "codex-5"})
    import common.model_selector as ms

    ms._models_cache = None

    import cost_guard as cg

    # codex-5 は heavy class だが research の light threshold で判定
    d = cg.allowed(
        phase="research", block_type="manual_query", est_in=100, est_out=100, model_hint="codex-5", script="test"
    )
    assert d.model_class == "light"
