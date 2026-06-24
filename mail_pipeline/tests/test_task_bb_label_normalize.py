# -*- coding: utf-8 -*-
"""Task BB: 分類ラベル正規化テスト。"""

from __future__ import annotations

import sys
from pathlib import Path

MAIL_PIPELINE_DIR = Path(__file__).resolve().parents[1]
SES_WORK = MAIL_PIPELINE_DIR.parent
for path in (str(SES_WORK), str(MAIL_PIPELINE_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from mail_pipeline.mail_pipeline import (
    _normalize_classify_results,
    get_label_norm_count,
    normalize_classify_label,
    normalize_classify_result,
    reset_label_norm_count,
)


def test_normalize_talent_to_engineer():
    assert normalize_classify_label("talent", "msg-1") == "engineer"


def test_normalize_resume_to_engineer():
    assert normalize_classify_label("resume") == "engineer"


def test_normalize_job_to_project():
    assert normalize_classify_label("job") == "project"


def test_unknown_label_becomes_other():
    assert normalize_classify_label("mystery_label", "msg-x") == "other"


def test_canonical_labels_pass_through():
    for label in ("project", "engineer", "skip", "other"):
        assert normalize_classify_label(label) == label
        assert normalize_classify_label(label.upper()) == label


def test_normalize_classify_result_updates_type():
    reset_label_norm_count()
    result = normalize_classify_result({"type": "resource", "note": "x"}, "mid-1")
    assert result["type"] == "engineer"


def test_normalize_classify_results_batch():
    reset_label_norm_count()
    results = {
        0: {"type": "talent"},
        1: {"type": "project"},
        2: {"type": "weird"},
    }
    emails = {0: {"msg_id": "a"}, 1: {"msg_id": "b"}, 2: {"msg_id": "c"}}
    normalized = _normalize_classify_results(results, emails)
    assert normalized[0]["type"] == "engineer"
    assert normalized[1]["type"] == "project"
    assert normalized[2]["type"] == "other"
    assert get_label_norm_count() == 2
