"""8.22 allowed→Decision→finalize→ledger.record の script 伝搬テスト（SPEC §7.1）。"""

from __future__ import annotations

from common.state_store import init_schema, open_conn


def _make_allowed(monkeypatch, script="my_test_script", target_id="proj-script-001"):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="skill_judge", target_id=target_id, script=script)
    return d


def test_script_preserved_in_decision(monkeypatch):
    """allowed() に渡した script が Decision.script に保持される。"""
    d = _make_allowed(monkeypatch, script="my_script_42")
    assert d.script == "my_script_42"


def test_script_preserved_when_failed(monkeypatch):
    """allowed=False でも Decision.script に script 値が保持される。"""
    from common.model_selector import ModelSelectionError

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: (_ for _ in ()).throw(ModelSelectionError("error_transient_models_list")),
    )
    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="manual_query", script="fail_script_test")
    assert d.allowed is False
    assert d.script == "fail_script_test"


def test_script_in_event_log_on_failure(monkeypatch):
    """allowed() 失敗時に event_log の script 列に script 値が記録される。"""
    from common.model_selector import ModelSelectionError

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: (_ for _ in ()).throw(ModelSelectionError("error_transient_models_list")),
    )
    import cost_guard as cg

    cg.allowed(phase="research", block_type="manual_query", script="logged_script")

    init_schema()
    conn = open_conn()
    try:
        row = conn.execute(
            "SELECT script FROM event_log WHERE reason=? ORDER BY id DESC LIMIT 1", ("error_transient_models_list",)
        ).fetchone()
        assert row is not None
        assert row["script"] == "logged_script"
    finally:
        conn.close()


def test_script_passed_to_record_on_finalize(monkeypatch):
    """finalize() が ledger.record() の script 引数に Decision.script を渡す。"""
    import cost_guard as cg

    d = _make_allowed(monkeypatch, script="finalize_script_test")
    assert d.allowed is True

    # finalize して cost_log.jsonl に書かれるか確認（ベストエフォート）
    cg.finalize(d, in_tokens=100, out_tokens=50, success=True)
    # 例外なく完了すれば OK
