# -*- coding: utf-8 -*-
"""nightly_jobz スケジューラ登録・検証テスト。"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SES_WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SES_WORK))

from nightly_jobz import verify_scheduler as vs


def test_verify_scheduler_ok_when_enabled(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "nightly_20260619.log").write_text("ok\n", encoding="utf-8")
    monkeypatch.setattr(vs, "LOG_DIR", log_dir)

    schtasks_output = """
タスク名: \\SES_NightlyJobz
状態: 準備完了
次回の実行時刻: 2026/06/19 23:55:00
最終実行時刻: 2026/06/18 23:55:01
最終結果: 0
実行するタスク: cmd.exe /c "C:\\ses_work\\wd_nightly_jobz.bat"
"""
    with patch.object(vs, "_query_task", return_value=schtasks_output):
        report = vs.verify_scheduler()

    assert report["ok"] is True


def test_verify_scheduler_ng_when_disabled(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "nightly_20260619.log").write_text("ok\n", encoding="utf-8")
    monkeypatch.setattr(vs, "LOG_DIR", log_dir)

    schtasks_output = """
タスク名: \\SES_NightlyJobz
状態: 無効
実行するタスク: cmd.exe /c "C:\\ses_work\\wd_nightly_jobz.bat"
"""
    with patch.object(vs, "_query_task", return_value=schtasks_output):
        report = vs.verify_scheduler()

    assert report["ok"] is False
