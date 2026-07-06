# -*- coding: utf-8 -*-
"""precision_improvement_unified Phase 4-6 スクリプトのテスト。"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SES_WORK = Path(__file__).resolve().parents[2]
MATCHING_V3 = SES_WORK / "matching_v3"
if str(SES_WORK) not in sys.path:
    sys.path.insert(0, str(SES_WORK))
if str(MATCHING_V3) not in sys.path:
    sys.path.insert(0, str(MATCHING_V3))


def test_script_bootstrap_paths():
    from script_bootstrap import bootstrap

    matching_v3_dir, ses_work = bootstrap()
    assert matching_v3_dir.name == "matching_v3"
    assert ses_work.name == "ses_work"
    assert str(matching_v3_dir) in sys.path
    assert str(ses_work) in sys.path


def test_cleanup_skills_imports():
    import cleanup_skills

    assert callable(cleanup_skills.run_cleanup)


def test_backfill_skills_imports():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "mv3_backfill_skills", MATCHING_V3 / "backfill_skills.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.run_backfill)


def test_retry_errors_dry_run_writes_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import retry_errors as re_mod

    db_path = tmp_path / "processed.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE processed_cases (
            case_id TEXT PRIMARY KEY,
            email_subject TEXT,
            business_status TEXT,
            retry_count INTEGER DEFAULT 0,
            updated_at TEXT
        )
        """
    )
    conn.executemany(
        "INSERT INTO processed_cases(case_id, email_subject, business_status, retry_count, updated_at) VALUES(?,?,?,?,?)",
        [
            ("case-1", "subj-1", "ERROR", 0, "2026-06-20 10:00:00"),
            ("case-2", "subj-2", "ERROR", 1, "2026-06-21 11:00:00"),
            ("case-3", "subj-3", "matched", 0, "2026-06-21 12:00:00"),
        ],
    )
    conn.commit()
    conn.close()

    report_dir = tmp_path / "research_results"
    monkeypatch.setattr(re_mod, "RESULTS_DIR", report_dir)

    import processed_db

    class _TestDB:
        def __init__(self) -> None:
            self.db_path = db_path

    monkeypatch.setattr(processed_db, "ProcessedDB", _TestDB)

    stats = re_mod.run_retry(batch_size=50, execute=False)
    assert stats["error_cases_found"] == 2
    assert len(stats["date_distribution"]) == 2

    reports = list(report_dir.glob("retry_errors_report_*.md"))
    assert len(reports) == 1
    content = reports[0].read_text(encoding="utf-8")
    assert "ERROR件数: 2" in content
    assert "2026-06-20" in content
