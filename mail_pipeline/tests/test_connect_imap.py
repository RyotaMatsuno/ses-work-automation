# -*- coding: utf-8 -*-
"""connect_imap timeout and retry tests."""

from __future__ import annotations

import imaplib
import socket
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mail_pipeline import mail_pipeline as mp


def test_connect_imap_sets_socket_timeout() -> None:
    mock_mail = MagicMock()
    with (
        patch("mail_pipeline.mail_pipeline.socket.setdefaulttimeout") as mock_timeout,
        patch("mail_pipeline.mail_pipeline.imaplib.IMAP4_SSL", return_value=mock_mail),
    ):
        result = mp.connect_imap("user@example.com", "secret")

    assert result is mock_mail
    mock_timeout.assert_any_call(mp.IMAP_TIMEOUT)
    mock_timeout.assert_any_call(None)
    mock_mail.login.assert_called_once_with("user@example.com", "secret")


def test_connect_imap_retries_then_raises() -> None:
    with (
        patch("mail_pipeline.mail_pipeline.time.sleep"),
        patch(
            "mail_pipeline.mail_pipeline.imaplib.IMAP4_SSL",
            side_effect=OSError("connection refused"),
        ),
    ):
        with pytest.raises(OSError, match="connection refused"):
            mp.connect_imap("user@example.com", "secret")


def test_connect_imap_succeeds_on_second_attempt() -> None:
    mock_mail = MagicMock()
    with (
        patch("mail_pipeline.mail_pipeline.time.sleep"),
        patch(
            "mail_pipeline.mail_pipeline.imaplib.IMAP4_SSL",
            side_effect=[socket.timeout("timed out"), mock_mail],
        ),
    ):
        result = mp.connect_imap("user@example.com", "secret")

    assert result is mock_mail
    mock_mail.login.assert_called_once_with("user@example.com", "secret")


def test_connect_imap_retries_imap_error() -> None:
    mock_mail = MagicMock()
    with (
        patch("mail_pipeline.mail_pipeline.time.sleep"),
        patch(
            "mail_pipeline.mail_pipeline.imaplib.IMAP4_SSL",
            side_effect=[imaplib.IMAP4.error("auth failed"), mock_mail],
        ),
    ):
        result = mp.connect_imap("user@example.com", "secret")

    assert result is mock_mail
