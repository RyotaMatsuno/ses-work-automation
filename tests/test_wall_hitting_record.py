# -*- coding: utf-8 -*-
"""wall_hitting.py — ledger.record が成功時に呼ばれることを確認するユニットテスト。"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
import requests


def _make_openai_resp(in_tok: int = 120, out_tok: int = 250) -> MagicMock:
    m = MagicMock()
    m.raise_for_status.return_value = None
    m.json.return_value = {
        "choices": [{"message": {"content": "GPT answer"}}],
        "usage": {"prompt_tokens": in_tok, "completion_tokens": out_tok},
    }
    return m


def _make_gemini_resp(in_tok: int = 80, out_tok: int = 150) -> MagicMock:
    m = MagicMock()
    m.status_code = 200
    m.raise_for_status.return_value = None
    m.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Gemini answer"}]}}],
        "usageMetadata": {"promptTokenCount": in_tok, "candidatesTokenCount": out_tok},
    }
    return m


def test_ledger_record_called_on_success(monkeypatch):
    """OpenAI/Gemini 両方成功時、ledger.record が計2回呼ばれ実トークンを使うこと。"""
    monkeypatch.setattr(sys, "argv", ["wall_hitting.py", "--problem", "テスト問題"])

    openai_resp = _make_openai_resp(in_tok=120, out_tok=250)
    gemini_resp = _make_gemini_resp(in_tok=80, out_tok=150)

    def fake_post(url, **kwargs):
        if "openai" in url:
            return openai_resp
        return gemini_resp

    mock_record = MagicMock()

    with (
        patch("wall_hitting.requests.post", side_effect=fake_post),
        patch("wall_hitting.ledger_record", mock_record),
        patch("wall_hitting._LEDGER_AVAILABLE", True),
        patch("wall_hitting.can_spend", return_value=True),
        patch("wall_hitting.load_api_keys", return_value=("fake-openai-key", "fake-gemini-key")),
        patch("wall_hitting._check_weekend_cap", return_value=True),
    ):
        import wall_hitting
        result = wall_hitting.main()

    assert result == 0
    assert mock_record.call_count >= 1

    # OpenAI record: 実トークン使用確認
    openai_call = mock_record.call_args_list[0]
    assert openai_call.args[0] == 120   # in_tokens
    assert openai_call.args[1] == 250   # out_tokens
    assert openai_call.kwargs.get("phase") == "wallhit"

    # Gemini record: 実トークン使用確認
    gemini_call = mock_record.call_args_list[1]
    assert gemini_call.args[0] == 80    # in_tokens
    assert gemini_call.args[1] == 150   # out_tokens
    assert gemini_call.kwargs.get("phase") == "wallhit"


def test_ledger_record_skipped_on_api_failure(monkeypatch):
    """API失敗時は ledger.record を呼ばないこと。"""
    monkeypatch.setattr(sys, "argv", ["wall_hitting.py", "--problem", "テスト問題"])

    fail_resp = MagicMock()
    fail_resp.raise_for_status.side_effect = requests.RequestException("connection error")

    mock_record = MagicMock()

    with (
        patch("wall_hitting.requests.post", return_value=fail_resp),
        patch("wall_hitting.ledger_record", mock_record),
        patch("wall_hitting._LEDGER_AVAILABLE", True),
        patch("wall_hitting.can_spend", return_value=True),
        patch("wall_hitting.load_api_keys", return_value=("fake-openai-key", "fake-gemini-key")),
        patch("wall_hitting._check_weekend_cap", return_value=True),
    ):
        import wall_hitting
        wall_hitting.main()

    mock_record.assert_not_called()


def test_ledger_record_uses_estimate_when_tokens_zero(monkeypatch):
    """APIが usage を返さない場合、動的推定値にフォールバックすること。"""
    problem = "テスト問題"
    monkeypatch.setattr(sys, "argv", ["wall_hitting.py", "--problem", problem])

    # usage フィールドなし
    openai_resp = MagicMock()
    openai_resp.raise_for_status.return_value = None
    openai_resp.json.return_value = {
        "choices": [{"message": {"content": "GPT answer"}}],
        # "usage" キーなし
    }

    gemini_resp = _make_gemini_resp(in_tok=0, out_tok=0)

    def fake_post(url, **kwargs):
        if "openai" in url:
            return openai_resp
        return gemini_resp

    mock_record = MagicMock()

    with (
        patch("wall_hitting.requests.post", side_effect=fake_post),
        patch("wall_hitting.ledger_record", mock_record),
        patch("wall_hitting._LEDGER_AVAILABLE", True),
        patch("wall_hitting.can_spend", return_value=True),
        patch("wall_hitting.load_api_keys", return_value=("fake-openai-key", "fake-gemini-key")),
        patch("wall_hitting._check_weekend_cap", return_value=True),
    ):
        import wall_hitting
        wall_hitting.main()

    assert mock_record.call_count >= 1
    # トークン0の場合は動的推定値（max(500, len(problem)//3)）にフォールバックすること
    # "テスト問題" = 5文字 → max(500, 5//3) = 500
    expected_est_in = max(500, len(problem) // 3)
    openai_call = mock_record.call_args_list[0]
    assert openai_call.args[0] == expected_est_in   # 推定値（500）
    assert openai_call.args[1] == 500               # est_out = max_tokens


def test_build_can_spend_est_dynamic():
    """_build_can_spend_est が入力長に連動した est_in を返すこと。"""
    import wall_hitting

    short_result = wall_hitting._build_can_spend_est("a" * 3, "gpt-4o", 500)
    long_result = wall_hitting._build_can_spend_est("a" * 4500, "gpt-4o", 500)

    # 短い問題: floor が効いて 500
    assert short_result[0] == 500
    # 長い問題: len(4500)//3=1500 > 500 → 1500
    assert long_result[0] == 1500
    # est_out は max_tokens そのまま
    assert short_result[1] == 500
    assert long_result[1] == 500


def test_build_can_spend_est_search_model_1_5x():
    """search モデルで 1.5倍係数が効くこと。"""
    import wall_hitting

    normal_in, normal_out = wall_hitting._build_can_spend_est("test", "gpt-4o", 500)
    search_in, search_out = wall_hitting._build_can_spend_est("test", "gpt-4o-search-preview", 500)

    assert search_in == int(normal_in * 1.5)
    assert search_out == int(normal_out * 1.5)


def test_can_spend_not_called_with_fixed_300(monkeypatch):
    """can_spend に固定値 300 が渡されないこと（OpenAI 通常モード）。"""
    monkeypatch.setattr(sys, "argv", ["wall_hitting.py", "--problem", "テスト"])

    mock_can_spend = MagicMock(return_value=True)

    with (
        patch("wall_hitting.requests.post", side_effect=lambda url, **kw: _make_openai_resp() if "openai" in url else _make_gemini_resp()),
        patch("wall_hitting.ledger_record", MagicMock()),
        patch("wall_hitting.can_spend", mock_can_spend),
        patch("wall_hitting._LEDGER_AVAILABLE", True),
        patch("wall_hitting.load_api_keys", return_value=("fake-key", "fake-gemini")),
        patch("wall_hitting._check_weekend_cap", return_value=True),
    ):
        import wall_hitting
        wall_hitting.main()

    for call in mock_can_spend.call_args_list:
        assert call.args[0] != 300, f"固定値 300 が渡された: {call}"
