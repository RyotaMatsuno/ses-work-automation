# -*- coding: utf-8 -*-
"""Task V P0-3: IMAP TLS verification tests."""

from __future__ import annotations

import os
import ssl
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import mail_pipeline.mail_pipeline as mp


def test_imap_ssl_context_requires_verification_by_default(monkeypatch):
    monkeypatch.delenv("IMAP_SKIP_TLS_VERIFY", raising=False)
    ctx = mp.create_imap_ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_imap_ssl_context_skip_when_env_set(monkeypatch):
    monkeypatch.setenv("IMAP_SKIP_TLS_VERIFY", "1")
    ctx = mp.create_imap_ssl_context()
    assert ctx.verify_mode == ssl.CERT_NONE
    assert ctx.check_hostname is False


def test_resolve_imap_connect_host_maps_ip_to_hostname():
    assert mp.resolve_imap_connect_host("118.27.122.112") == "mail65.onamae.ne.jp"
    assert mp.resolve_imap_connect_host("mail65.onamae.ne.jp") == "mail65.onamae.ne.jp"


@pytest.mark.integration
def test_imap_connect_mail65_with_tls_verification(monkeypatch):
    """Connect to production IMAP with certificate verification enabled."""
    monkeypatch.delenv("IMAP_SKIP_TLS_VERIFY", raising=False)
    from dotenv import dotenv_values

    env = dotenv_values(Path(__file__).resolve().parents[2] / "config" / ".env")
    user = os.environ.get("OUTLOOK_EMAIL") or env.get("OUTLOOK_EMAIL", "")
    password = os.environ.get("OUTLOOK_PASSWORD") or env.get("OUTLOOK_PASSWORD", "")
    if not user or not password:
        pytest.skip("OUTLOOK credentials not configured")

    ctx = mp.create_imap_ssl_context()
    mail = mp.connect_imap(user, password, ssl_context=ctx)
    try:
        mail.logout()
    except Exception:
        pass


def test_imap_connect_rejects_invalid_certificate(monkeypatch):
    monkeypatch.delenv("IMAP_SKIP_TLS_VERIFY", raising=False)
    ctx = mp.create_imap_ssl_context()
    with pytest.raises(Exception):
        with patch.object(mp, "IMAP_SERVER", "self-signed.badssl.com"):
            mp.connect_imap("user@example.com", "secret", ssl_context=ctx)
