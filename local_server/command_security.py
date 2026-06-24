# -*- coding: utf-8 -*-
"""Security helpers for command_server (allowlist, localhost checks)."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

ALLOWED_COMMANDS = frozenset({"python", "pythonw", "pip", "rg", "echo", "type", "dir"})
SHELL_METACHAR_RE = re.compile(r"[;|&`$<>]|&&|\|\|")
LOCALHOST_ADDRS = frozenset({"127.0.0.1", "::1"})
LOCALHOST_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]", ""})


def validate_command(cmd: str) -> list[str]:
    """Parse cmd string into argv for shell=False execution."""
    stripped = (cmd or "").strip()
    if not stripped:
        raise ValueError("cmd is required")
    if SHELL_METACHAR_RE.search(stripped):
        raise ValueError("shell metacharacters not allowed")
    try:
        parts = shlex.split(stripped, posix=False)
    except ValueError as exc:
        raise ValueError(f"invalid command syntax: {exc}") from exc
    if not parts:
        raise ValueError("cmd is required")
    exe_name = Path(parts[0]).name.lower()
    if exe_name.endswith(".exe"):
        exe_name = exe_name[:-4]
    if exe_name not in ALLOWED_COMMANDS:
        raise ValueError(f"command not allowed: {parts[0]}")
    return parts


def is_localhost_request(client_address: tuple[str, int], host_header: str) -> bool:
    if client_address[0] not in LOCALHOST_ADDRS:
        return False
    host_only = (host_header or "").split(":")[0].lower()
    return host_only in LOCALHOST_HOSTS
