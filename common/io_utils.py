# -*- coding: utf-8 -*-
"""
共通 I/O ユーティリティ

すべてのスクリプトがモジュールレベルで呼ぶ stdout/stderr 設定を一元管理する。
pythonw（コンソールなし）環境での AttributeError を安全に吸収する。
"""

from __future__ import annotations

import sys


def setup_stdout(encoding: str = "utf-8", errors: str = "replace") -> None:
    """
    stdout / stderr を指定エンコーディングに設定する。
    pythonw 等で stdout が None の場合は何もしない（例外を握りつぶさない）。
    """
    if sys.stdout is not None:
        try:
            sys.stdout.reconfigure(encoding=encoding, errors=errors)
        except Exception:
            pass
    if sys.stderr is not None:
        try:
            sys.stderr.reconfigure(encoding=encoding, errors=errors)
        except Exception:
            pass
