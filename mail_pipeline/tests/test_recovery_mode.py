# -*- coding: utf-8 -*-
"""recovery_mode.py のユニットテスト (6件以上)。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest


def _make_module_with_tmp_state(tmp_path):
    """recovery_mode をインポートし、STATE_PATH を tmp_path に差し替えたモジュールを返す。"""
    import mail_pipeline.recovery_mode as rm

    # 一時ファイルにパスを書き換え
    orig = rm.STATE_PATH
    rm.STATE_PATH = tmp_path / "recovery_state.json"
    yield rm
    rm.STATE_PATH = orig


@pytest.fixture
def rm_module(tmp_path):
    import mail_pipeline.recovery_mode as rm

    orig = rm.STATE_PATH
    rm.STATE_PATH = tmp_path / "recovery_state.json"
    yield rm
    rm.STATE_PATH = orig


def _ok_metrics():
    return {"exit_code": 0, "notion_errors": 0, "imap_errors": 0, "ts_end": "2026-06-18T10:00:00"}


def _fail_metrics():
    return {"exit_code": 1, "notion_errors": 0, "imap_errors": 0, "ts_end": "2026-06-18T10:00:00"}


# ===== テスト1: 初期状態読み込み =====
def test_load_default_state(rm_module):
    state = rm_module.load_state()
    assert state["current_phase"] == "day0_emergency"
    assert state["process_limit"] == 10
    assert state["fetch_limit"] == 50


# ===== テスト2: get_limits が正しいlimitを返す =====
def test_get_limits_day0(rm_module):
    state = rm_module.load_state()
    pl, fl = rm_module.get_limits(state)
    assert pl == 10
    assert fl == 50


def test_get_limits_day3(rm_module):
    state = rm_module.load_state()
    state["current_phase"] = "day3_normal"
    pl, fl = rm_module.get_limits(state)
    assert pl == 50
    assert fl == 200


# ===== テスト3: 4連続成功で昇格提案が生成される =====
def test_promotion_after_4_successes(rm_module):
    state = rm_module.load_state()
    for _ in range(3):
        result = rm_module.evaluate_promotion(state, _ok_metrics())
        assert result == "none"
    result = rm_module.evaluate_promotion(state, _ok_metrics())
    assert result == "promote"
    assert state["promotion_proposal_pending"] is True
    assert state["promotion_proposal_to"] == "day1_warmup"


# ===== テスト4: 2連続失敗で縮退が実行される =====
def test_demotion_after_2_failures(rm_module):
    state = rm_module.load_state()
    state["current_phase"] = "day1_warmup"
    rm_module._apply_phase(state, "day1_warmup")

    result = rm_module.evaluate_promotion(state, _fail_metrics())
    assert result == "none"
    result = rm_module.evaluate_promotion(state, _fail_metrics())
    assert result == "demote"
    assert state["current_phase"] == "day0_emergency"


# ===== テスト5: day0_emergency は縮退しない =====
def test_no_demotion_below_day0(rm_module):
    state = rm_module.load_state()
    assert state["current_phase"] == "day0_emergency"
    # 2回失敗しても縮退なし（これ以上下がれない）
    for _ in range(3):
        result = rm_module.evaluate_promotion(state, _fail_metrics())
        assert result == "none"
    assert state["current_phase"] == "day0_emergency"


# ===== テスト6: 昇格OK で次フェーズに移行する =====
def test_confirm_promotion_ok(rm_module):
    state = rm_module.load_state()
    # 4連続成功で昇格提案生成
    for _ in range(4):
        rm_module.evaluate_promotion(state, _ok_metrics())
    assert state["promotion_proposal_pending"] is True
    assert state["promotion_proposal_to"] == "day1_warmup"

    ok = rm_module.confirm_promotion(state, "OK", decided_by="松野")
    assert ok is True
    assert state["current_phase"] == "day1_warmup"
    assert state["promotion_proposal_pending"] is False
    assert state["consecutive_success_count"] == 0


# ===== テスト7: 昇格却下でフェーズ維持 =====
def test_confirm_promotion_reject(rm_module):
    state = rm_module.load_state()
    for _ in range(4):
        rm_module.evaluate_promotion(state, _ok_metrics())
    rm_module.confirm_promotion(state, "却下")
    assert state["current_phase"] == "day0_emergency"
    assert state["promotion_proposal_pending"] is False


# ===== テスト8: Day0→Day1→Day2→Day3 フェーズ遷移シミュレーション =====
def test_full_phase_progression(rm_module):
    state = rm_module.load_state()
    phases = ["day0_emergency", "day1_warmup", "day2_warmup", "day3_normal"]
    for expected_phase, next_phase in zip(phases, phases[1:]):
        assert state["current_phase"] == expected_phase
        for _ in range(4):
            rm_module.evaluate_promotion(state, _ok_metrics())
        assert state["promotion_proposal_pending"] is True
        rm_module.confirm_promotion(state, "OK", decided_by="松野")
        assert state["current_phase"] == next_phase

    # day3_normal ではこれ以上昇格しない
    for _ in range(5):
        result = rm_module.evaluate_promotion(state, _ok_metrics())
        assert result == "none"


# ===== テスト9: manual_set_phase で任意フェーズに設定できる =====
def test_manual_set_phase(rm_module):
    ok = rm_module.manual_set_phase("day3_normal")
    assert ok is True
    state = rm_module.load_state()
    assert state["current_phase"] == "day3_normal"
    assert state["process_limit"] == 50
    assert state["fetch_limit"] == 200


# ===== テスト10: 昇格提案メッセージのフォーマット確認 =====
def test_build_promote_message(rm_module):
    state = rm_module.load_state()
    state["promotion_proposal_pending"] = True
    state["promotion_proposal_to"] = "day1_warmup"
    state["consecutive_success_count"] = 4
    msg = rm_module.build_promote_message(state)
    assert "昇格提案" in msg
    assert "day0_emergency" in msg
    assert "day1_warmup" in msg
    assert "昇格OK" in msg
