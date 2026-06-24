"""テスト共通フィクスチャ。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


@pytest.fixture(autouse=True)
def isolated_state_dir(tmp_path, monkeypatch):
    """各テストが独立した sqlite DB を使うよう STATE_DIR を tmp_path に設定する。"""
    state_dir = tmp_path / "ses_work_state"
    state_dir.mkdir()
    monkeypatch.setenv("STATE_DIR", str(state_dir))
    # state_store のキャッシュをリセット
    try:
        import common.state_store as _ss

        _ss._ENV.pop("STATE_DIR", None)
    except Exception:
        pass
    # ledger のモデルレートキャッシュもリセット
    try:
        import common.ledger as _l

        _l._model_rates = None
    except Exception:
        pass
    # model_selector のキャッシュをリセット
    try:
        import common.model_selector as _ms

        _ms._models_cache = None
        _ms._consecutive_failures = 0
    except Exception:
        pass
    yield state_dir
