"""Mock tests for pdca_monitor (no external API calls)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

BASE_DIR = Path(__file__).resolve().parent
SES_WORK = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(SES_WORK))

import db  # noqa: E402
import ocr  # noqa: E402
import reporter  # noqa: E402

JST = timezone(timedelta(hours=9))


class TestDb(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.original_db = db.DB_PATH
        db.DB_PATH = Path(self.tmp.name) / "activity.db"
        db.DATA_DIR = db.DB_PATH.parent
        db.init_db()

    def tearDown(self) -> None:
        db.DB_PATH = self.original_db
        db.DATA_DIR = self.original_db.parent
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def test_weekly_summary(self) -> None:
        today = datetime.now(JST).date()
        for i in range(3):
            ts = datetime.combine(today, datetime.min.time()).replace(tzinfo=JST)
            ts = ts + timedelta(minutes=i * 5)
            db.insert_activity(
                ts.isoformat(),
                "Cursor.exe",
                f"test window {i}",
                "Python 自動化 Notion",
                None,
            )
        start = (today - timedelta(days=today.weekday())).isoformat()
        end = (datetime.strptime(start, "%Y-%m-%d").date() + timedelta(days=6)).isoformat()
        summary = db.get_weekly_summary(start, end)
        self.assertGreaterEqual(summary["record_count"], 3)
        self.assertEqual(summary["app_usage"][0]["app_name"], "Cursor.exe")
        self.assertGreaterEqual(summary["app_usage"][0]["minutes"], 15)


class TestOcr(unittest.TestCase):
    def test_mask_password(self) -> None:
        raw = "password: secret123\napi_key=abcd1234\nカード 4111 1111 1111 1111"
        masked = ocr.mask_sensitive_text(raw)
        self.assertIn("[MASKED]", masked)
        self.assertNotIn("secret123", masked)
        self.assertNotIn("4111", masked)


class TestReporterMock(unittest.TestCase):
    def test_mock_report(self) -> None:
        result = reporter.run_report(mock=True)
        self.assertIn("週次PDCAレポート", result["line_message"])
        self.assertIn("自動化提案", result["line_message"])
        self.assertIn("automation_suggestions", result["ai_content"])


if __name__ == "__main__":
    unittest.main()
