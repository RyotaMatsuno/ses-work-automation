# -*- coding: utf-8 -*-
"""run_flag_updater logging setup tests."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

SES_WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SES_WORK))

from flag_auto_updater.run_flag_updater import _setup_logging


@pytest.fixture(autouse=True)
def reset_root_logger():
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    yield
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    for handler in saved_handlers:
        root.addHandler(handler)
    root.setLevel(saved_level)


def test_standalone_setup_creates_file_and_stream_handlers(tmp_path, monkeypatch):
    monkeypatch.setattr("flag_auto_updater.run_flag_updater.BASE_DIR", tmp_path)
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    _setup_logging()
    file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
    stream_handlers = [
        h
        for h in root.handlers
        if isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.FileHandler)
    ]
    assert len(file_handlers) == 1
    assert len(stream_handlers) == 1
    assert "flag_updater_" in getattr(file_handlers[0], "baseFilename", "")


def test_subroutine_setup_preserves_existing_handlers(tmp_path, monkeypatch):
    monkeypatch.setattr("flag_auto_updater.run_flag_updater.BASE_DIR", tmp_path)
    matching_log = tmp_path / "logs" / "matching_v3_20260619.log"
    matching_log.parent.mkdir(parents=True, exist_ok=True)

    matching_handler = logging.FileHandler(matching_log, encoding="utf-8")
    logging.getLogger().addHandler(matching_handler)

    _setup_logging()

    root = logging.getLogger()
    file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
    paths = {getattr(h, "baseFilename", "") for h in file_handlers}
    assert str(matching_log) in paths
    assert any("flag_updater_" in p for p in paths)
    assert len(file_handlers) == 2


def test_subroutine_setup_writes_to_both_logs(tmp_path, monkeypatch):
    monkeypatch.setattr("flag_auto_updater.run_flag_updater.BASE_DIR", tmp_path)
    matching_log = tmp_path / "logs" / "matching_v3_20260619.log"
    matching_log.parent.mkdir(parents=True, exist_ok=True)

    matching_handler = logging.FileHandler(matching_log, encoding="utf-8")
    matching_handler.setLevel(logging.INFO)
    matching_handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(matching_handler)

    _setup_logging()
    logging.getLogger("matching_v3").info("matching-log-line")

    assert "matching-log-line" in matching_log.read_text(encoding="utf-8")
    flag_logs = list((tmp_path / "logs").glob("flag_updater_*.log"))
    assert len(flag_logs) == 1
    assert "matching-log-line" in flag_logs[0].read_text(encoding="utf-8")
