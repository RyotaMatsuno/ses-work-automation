# -*- coding: utf-8 -*-
import os
from urllib.parse import urlparse

import requests
from dotenv import dotenv_values

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "config", ".env")
config = dotenv_values(ENV_PATH)

_BLOCKED_URL_PATTERNS = ("trycloudflare.com", "cloudflared")
_DEFAULT_COMMAND_URL = "http://127.0.0.1:8765"


def _resolve_command_url() -> str:
    """Resolve localhost-only command server URL. Cloudflare tunnel URLs are blocked."""
    raw = os.environ.get("JOBZ_COMMAND_URL") or config.get("JOBZ_COMMAND_URL") or _DEFAULT_COMMAND_URL
    url = raw.rstrip("/")
    lower = url.lower()
    if any(pattern in lower for pattern in _BLOCKED_URL_PATTERNS):
        return _DEFAULT_COMMAND_URL
    parsed = urlparse(url)
    if parsed.hostname not in ("127.0.0.1", "localhost"):
        raise ValueError("JOBZ_COMMAND_URLはlocalhostのみ許可されています")
    return url


JOBZ_COMMAND_URL = _resolve_command_url()
JOBZ_AUTH_TOKEN = (
    os.environ.get("JOBZ_COMMAND_TOKEN")
    or os.environ.get("JOBZ_AUTH_TOKEN")
    or config.get("JOBZ_COMMAND_TOKEN")
    or config.get("JOBZ_AUTH_TOKEN")
    or ""
)
HEADERS = {"X-Auth-Token": JOBZ_AUTH_TOKEN, "Content-Type": "application/json"}
TIMEOUT = 30


def trim_result(text, max=200):
    text = "" if text is None else str(text)
    return text[:max] + ("..." if len(text) > max else "")


def _endpoint(path):
    if not JOBZ_COMMAND_URL:
        raise ValueError("JOBZ_COMMAND_URLが未設定です")
    return f"{JOBZ_COMMAND_URL.rstrip('/')}/{path.lstrip('/')}"


def _error_message(error):
    return f"❌ エラー\n{trim_result(error, 200)}"


def execute_remote(cmd):
    cmd = (cmd or "").strip()
    if not cmd:
        return _error_message("コマンドが空です")

    try:
        res = requests.post(
            _endpoint("/run"),
            headers=HEADERS,
            json={"cmd": cmd, "cwd": "ses_work"},
            timeout=TIMEOUT,
        )
        if res.status_code >= 400:
            return _error_message(f"HTTP {res.status_code}: {res.text[:200]}")

        data = res.json()
        stdout = data.get("stdout", "")
        stderr = data.get("stderr", "")
        returncode = data.get("returncode", 0)

        if returncode == 0:
            output = stdout or stderr or "出力なし"
            return f"✅ 実行完了\n{trim_result(output, 200)}"

        error = stderr or stdout or f"returncode={returncode}"
        return _error_message(error)
    except Exception as e:
        return _error_message(str(e))


def execute_bg(cmd):
    cmd = (cmd or "").strip()
    if not cmd:
        return _error_message("コマンドが空です")

    try:
        res = requests.post(
            _endpoint("/run_bg"),
            headers=HEADERS,
            json={"cmd": cmd, "cwd": "ses_work"},
            timeout=TIMEOUT,
        )
        if res.status_code >= 400:
            return _error_message(f"HTTP {res.status_code}: {res.text[:200]}")

        return f"✅ バックグラウンド実行開始\n{trim_result(cmd, 200)}"
    except Exception as e:
        return _error_message(str(e))


def get_log():
    try:
        res = requests.get(_endpoint("/log"), headers=HEADERS, timeout=TIMEOUT)
        if res.status_code >= 400:
            return _error_message(f"HTTP {res.status_code}: {res.text[:200]}")

        try:
            data = res.json()
            log_text = data.get("log") or data.get("stdout") or data.get("text") or ""
        except ValueError:
            log_text = res.text

        lines = str(log_text).splitlines()[-50:]
        return trim_result("\n".join(lines), 2000)
    except Exception as e:
        return _error_message(str(e))


def get_health():
    try:
        res = requests.get(_endpoint("/health"), headers=HEADERS, timeout=TIMEOUT)
        if res.status_code >= 400:
            return f"❌ 接続失敗: HTTP {res.status_code}"

        return "✅ jobz-command: OK"
    except Exception as e:
        return f"❌ 接続失敗: {trim_result(e, 200)}"
