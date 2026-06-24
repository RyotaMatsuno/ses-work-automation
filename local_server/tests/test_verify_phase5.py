# -*- coding: utf-8 -*-
"""local_server Phase5 検証スクリプトの単体テスト。"""

from __future__ import annotations

import json
import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SES_WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SES_WORK))

from local_server import verify_phase5 as vp


class _FakeResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_git_status_ok(monkeypatch):
    def fake_urlopen(req, timeout=120):
        if req.full_url.endswith("/health"):
            return _FakeResponse({"status": "ok"})
        return _FakeResponse({"returncode": 0, "stdout": " M file.py\n", "stderr": ""})

    monkeypatch.setattr(vp.urllib.request, "urlopen", fake_urlopen)
    ok, msg = vp.test_git_status()
    assert ok is True
    assert "OK" in msg


def test_write_and_run_ok(monkeypatch, tmp_path):
    script = tmp_path / "_phase5_test_script.py"
    monkeypatch.setattr(vp, "SES_WORK", tmp_path)

    def fake_urlopen(req, timeout=120):
        return _FakeResponse(
            {
                "written": True,
                "returncode": 0,
                "stdout": "PHASE5_OK\n",
                "stderr": "",
            }
        )

    monkeypatch.setattr(vp.urllib.request, "urlopen", fake_urlopen)
    ok, msg = vp.test_write_and_run()
    assert ok is True


def test_run_all_fails_when_server_down(monkeypatch):
    def fake_urlopen(*args, **kwargs):
        raise vp.urllib.error.URLError("connection refused")

    monkeypatch.setattr(vp.urllib.request, "urlopen", fake_urlopen)
    results = vp.run_all()
    assert results["health"][0] is False
