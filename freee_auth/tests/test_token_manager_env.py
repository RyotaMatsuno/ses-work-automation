# -*- coding: utf-8 -*-
"""Task V P0-8: freee OAuth credentials must come from environment."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

FREE_AUTH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FREE_AUTH_DIR.parent))


def test_token_manager_has_no_hardcoded_secrets():
    source = (FREE_AUTH_DIR / "token_manager.py").read_text(encoding="utf-8")
    assert 'CLIENT_SECRET = "' not in source
    assert 'CLIENT_ID = "' not in source or "os.environ" in source


def test_get_client_credentials_requires_env(monkeypatch):
    monkeypatch.setenv("FREEE_CLIENT_ID", "")
    monkeypatch.setenv("FREEE_CLIENT_SECRET", "")

    import freee_auth.token_manager as tm

    importlib.reload(tm)
    with pytest.raises(RuntimeError, match="FREEE_CLIENT"):
        tm.get_client_credentials()
