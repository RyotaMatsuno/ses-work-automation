# -*- coding: utf-8 -*-
"""Task 5: Windowsタスクスケジューラ自動実行確認テスト。"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SES_WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SES_WORK))

from mail_pipeline import verify_scheduler as vs


def test_verify_scheduler_ok_when_enabled_and_log_recent(tmp_path, monkeypatch):
    pipeline_log = tmp_path / "pipeline.log"
    pipeline_log.write_text("START\n", encoding="utf-8")
    monkeypatch.setattr(vs, "PIPELINE_LOG", pipeline_log)

    schtasks_output = """
タスク名: \\SES_MailPipeline
状態: 準備完了
次回の実行時刻: 2026/06/19 20:00:00
最終実行時刻: 2026/06/19 19:00:00
最終結果: 0
実行するタスク: cmd.exe /c "C:\\ses_work\\wd_mail_pipeline.bat"
"""
    with patch.object(vs, "_query_task", return_value=schtasks_output):
        report = vs.verify_scheduler()

    assert report["ok"] is True
    assert report["pipeline_log_recent"] is True


def test_verify_scheduler_ng_when_disabled(tmp_path, monkeypatch):
    pipeline_log = tmp_path / "pipeline.log"
    pipeline_log.write_text("START\n", encoding="utf-8")
    monkeypatch.setattr(vs, "PIPELINE_LOG", pipeline_log)

    schtasks_output = """
タスク名: \\SES_MailPipeline
状態: 無効
実行するタスク: cmd.exe /c "C:\\ses_work\\wd_mail_pipeline.bat"
"""
    with patch.object(vs, "_query_task", return_value=schtasks_output):
        report = vs.verify_scheduler()

    assert report["ok"] is False
    assert "無効" in report["notes"] or "Disabled" in report["notes"]
