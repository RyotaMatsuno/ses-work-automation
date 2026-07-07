"""Tests for scripts/secret_scan.py"""
import sys
import io
import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "scripts"))
from secret_scan import scan_bytes, scan_file

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _hits_names(raw: bytes) -> list[str]:
    return [name for name, _ in scan_bytes(raw)]


# ---------------------------------------------------------------------------
# pattern detection
# ---------------------------------------------------------------------------

def test_openai_key_detected():
    raw = b"token = 'sk-abcdefghijklmnopqrstuvwxyz1234'"
    assert "OpenAI key" in _hits_names(raw)


def test_gcp_api_key_detected():
    raw = b"key=AIzaSyAbcdefghijklmnopqrstuvwxyz1234567"
    assert "GCP API key" in _hits_names(raw)


def test_private_key_detected():
    raw = b"-----BEGIN RSA PRIVATE KEY-----\nMIIE..."
    assert "Private key" in _hits_names(raw)


def test_gcp_oauth_token_detected():
    raw = b"access_token=ya29.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV"
    assert "GCP OAuth token" in _hits_names(raw)


def test_line_channel_token_detected():
    raw = b"LINE_TOKEN=" + b"A" * 140
    assert "LINE channel token" in _hits_names(raw)


def test_no_false_positive_short_string():
    raw = b"short_token=abc123"
    assert _hits_names(raw) == []


# ---------------------------------------------------------------------------
# UTF-16 mixed byte detection
# ---------------------------------------------------------------------------

def test_utf16_openai_key_detected():
    secret = b"sk-secretkey1234567890abcdefghij"
    # Simulate UTF-16 LE encoding with null bytes between each char
    raw_utf16 = b"\x00".join([bytes([c]) for c in secret]) + b"\x00"
    names = _hits_names(raw_utf16)
    assert "OpenAI key" in names


def test_utf16_gcp_key_detected():
    secret = b"AIzaXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    raw_utf16 = b"\x00".join([bytes([c]) for c in secret]) + b"\x00"
    assert "GCP API key" in _hits_names(raw_utf16)


# ---------------------------------------------------------------------------
# scan_file + value not in stdout
# ---------------------------------------------------------------------------

def test_scan_file_detects_secret(tmp_path):
    f = tmp_path / "config.py"
    f.write_bytes(b"OPENAI_KEY = 'sk-testkey1234567890abcdefghijklmn'\n")
    hits = scan_file(str(f))
    assert any(name == "OpenAI key" for name, _ in hits)


def test_scan_file_reports_correct_line(tmp_path):
    f = tmp_path / "config.py"
    f.write_bytes(b"# line 1\n# line 2\nOPENAI = 'sk-testkey1234567890abcdefghijklmn'\n")
    hits = scan_file(str(f))
    assert hits[0][1] == 3  # secret is on line 3


def test_scan_file_clean_returns_empty(tmp_path):
    f = tmp_path / "clean.py"
    f.write_bytes(b"x = 1\nprint('hello')\n")
    assert scan_file(str(f)) == []


def test_secret_value_not_in_output(tmp_path, capsys):
    """scan_bytes must not print the secret value."""
    secret = b"sk-mysupersecretkey1234567890abcde"
    raw = b"KEY = '" + secret + b"'\n"
    hits = scan_bytes(raw)
    assert hits  # must detect

    # Simulate what main() would print
    for name, line_num in hits:
        print(f"[BLOCKED] fake_file.py:{line_num} — {name} detected")

    captured = capsys.readouterr()
    assert secret.decode() not in captured.out
    assert "sk-" not in captured.out  # no partial leak either
