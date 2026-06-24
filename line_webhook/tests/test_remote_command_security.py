# -*- coding: utf-8 -*-
"""Task V P0-7: remote_command_handler tunnel blocking tests."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_cloudflare_tunnel_falls_back_to_localhost(monkeypatch):
    monkeypatch.setenv("JOBZ_COMMAND_URL", "https://evil.trycloudflare.com")
    monkeypatch.delenv("JOBZ_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("JOBZ_COMMAND_TOKEN", raising=False)

    import line_webhook.remote_command_handler as rch

    importlib.reload(rch)
    assert rch.JOBZ_COMMAND_URL == "http://127.0.0.1:8765"


def test_non_localhost_url_rejected(monkeypatch):
    monkeypatch.setenv("JOBZ_COMMAND_URL", "http://192.168.1.10:8765")
    monkeypatch.delenv("JOBZ_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("JOBZ_COMMAND_TOKEN", raising=False)

    import line_webhook.remote_command_handler as rch

    with pytest.raises(ValueError, match="localhost"):
        importlib.reload(rch)
