# -*- coding: utf-8 -*-
"""Task V P0-7: command_server security tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from command_security import is_localhost_request, validate_command


def test_allowlist_accepts_python():
    argv = validate_command("python -m pytest -q")
    assert argv[0] == "python"


def test_allowlist_accepts_dir_and_type():
    assert validate_command("dir")[0] == "dir"
    assert validate_command("type README.md")[0] == "type"


def test_allowlist_rejects_rm():
    with pytest.raises(ValueError, match="not allowed"):
        validate_command("rm -rf /")


def test_shell_injection_rejected():
    with pytest.raises(ValueError, match="metacharacters"):
        validate_command("python -c 'import os'; rm -rf /")
    with pytest.raises(ValueError, match="metacharacters"):
        validate_command("echo hello && del /f /q *")


def test_localhost_request_accepts_loopback():
    assert is_localhost_request(("127.0.0.1", 12345), "localhost:8765") is True
    assert is_localhost_request(("::1", 12345), "127.0.0.1:8765") is True


def test_localhost_request_rejects_remote_addr():
    assert is_localhost_request(("192.168.1.10", 12345), "localhost:8765") is False


def test_localhost_request_rejects_foreign_host_header():
    assert is_localhost_request(("127.0.0.1", 12345), "evil.example.com:8765") is False
