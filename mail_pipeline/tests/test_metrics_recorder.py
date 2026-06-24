# -*- coding: utf-8 -*-
"""MetricsRecorder のユニットテスト (4件以上)。"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest


@pytest.fixture
def recorder(tmp_path, monkeypatch):
    import mail_pipeline.metrics_recorder as mr

    monkeypatch.setattr(mr, "METRICS_PATH", tmp_path / "metrics.jsonl")
    from mail_pipeline.metrics_recorder import MetricsRecorder

    return MetricsRecorder(), mr.METRICS_PATH


# ===== テスト1: finalize がファイルに書き込む =====
def test_finalize_writes_file(recorder):
    rec, path = recorder
    rec.inc("mails_fetched", 10)
    result = rec.finalize(exit_code=0)
    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["exit_code"] == 0
    assert data["mails_fetched"] == 10


# ===== テスト2: inc が正しく加算される =====
def test_inc_accumulates(recorder):
    rec, path = recorder
    rec.inc("notion_engineer_created", 3)
    rec.inc("notion_engineer_created", 2)
    result = rec.finalize()
    assert result["notion_engineer_created"] == 5


# ===== テスト3: set が値を上書きする =====
def test_set_overwrites(recorder):
    rec, path = recorder
    rec.set("fetch_limit", 50)
    rec.set("fetch_limit", 200)
    result = rec.finalize()
    assert result["fetch_limit"] == 200


# ===== テスト4: elapsed_seconds が正の値 =====
def test_elapsed_seconds_positive(recorder):
    rec, path = recorder
    time.sleep(0.01)
    result = rec.finalize()
    assert result["elapsed_seconds"] > 0


# ===== テスト5: error_message が 500文字に切り詰められる =====
def test_error_message_truncated(recorder):
    rec, path = recorder
    long_msg = "x" * 1000
    result = rec.finalize(exit_code=1, error_message=long_msg)
    assert len(result["error_message"]) == 500


# ===== テスト6: 複数回 finalize 呼び出しで行が追加される =====
def test_multiple_runs_append(tmp_path, monkeypatch):
    import mail_pipeline.metrics_recorder as mr

    monkeypatch.setattr(mr, "METRICS_PATH", tmp_path / "metrics.jsonl")
    from mail_pipeline.metrics_recorder import MetricsRecorder

    MetricsRecorder().finalize(exit_code=0)
    MetricsRecorder().finalize(exit_code=1, error_message="err")
    lines = (tmp_path / "metrics.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[1])["exit_code"] == 1
