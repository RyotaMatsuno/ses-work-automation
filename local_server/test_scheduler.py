# -*- coding: utf-8 -*-
"""scheduler.py の単体テスト"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import scheduler


class SchedulerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.state_path = base / "state.json"
        self.lock_path = base / "lock"
        self.log_dir = base / "logs"
        self.log_dir.mkdir()
        self.bat_path = base / "wd_mail_pipeline.bat"
        self.bat_path.write_text("@echo off\necho ok\n", encoding="utf-8")

        patchers = [
            mock.patch.object(scheduler, "STATE_PATH", self.state_path),
            mock.patch.object(scheduler, "LOCK_PATH", self.lock_path),
            mock.patch.object(scheduler, "JOB_STATE_DIR", base),
            mock.patch.object(scheduler, "HOURLY_LOG_DIR", self.log_dir),
            mock.patch.object(scheduler, "PIPELINE_BAT", self.bat_path),
            mock.patch.object(scheduler, "SES_WORK_DIR", base),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        scheduler._current_run = None
        scheduler.release_file_lock()
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(dict(scheduler.DEFAULT_STATE), f)

    def test_status_defaults(self) -> None:
        status = scheduler.get_status()
        self.assertIn("running", status)
        self.assertIn("next_due_at", status)
        self.assertFalse(status["running"])

    def test_history_empty(self) -> None:
        self.assertEqual(scheduler.get_history(limit=5), [])

    def test_manual_run_success(self) -> None:
        with mock.patch("scheduler.subprocess.Popen") as popen:
            proc = mock.Mock()
            proc.wait.return_value = 0
            popen.return_value = proc
            result = scheduler.run_manual()
        self.assertTrue(result["ok"])
        self.assertEqual(result["exit_code"], 0)
        status = scheduler.get_status()
        self.assertEqual(status["last_exit_code"], 0)
        self.assertEqual(len(scheduler.get_history()), 1)

    def test_double_run_blocked(self) -> None:
        self.assertTrue(scheduler.acquire_file_lock())
        try:
            result = scheduler.run_manual()
            self.assertFalse(result["ok"])
            self.assertEqual(result["reason"], "already_running")
        finally:
            scheduler.release_file_lock()

    def test_catch_up_runs_missed_slot(self) -> None:
        past = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
        state = scheduler.load_state()
        state["last_scheduled_slot"] = scheduler._slot_iso(past)
        scheduler.save_state(state)

        with mock.patch("scheduler.subprocess.Popen") as popen:
            proc = mock.Mock()
            proc.wait.return_value = 0
            popen.return_value = proc
            scheduler._process_due_slots(datetime.now(), catch_up=True)

        updated = scheduler.load_state()
        self.assertIsNotNone(updated["last_scheduled_slot"])
        self.assertGreaterEqual(len(updated["history"]), 1)

    def test_handle_get_status_and_history(self) -> None:
        code, data = scheduler.handle_get("/jobs/mail_pipeline/status")
        self.assertEqual(code, 200)
        self.assertIn("next_due_at", data)

        code, data = scheduler.handle_get("/jobs/mail_pipeline/history?limit=10")
        self.assertEqual(code, 200)
        self.assertIn("history", data)

    def test_handle_post_run_deprecated(self) -> None:
        code, data = scheduler.handle_post("/jobs/mail_pipeline/run")
        self.assertEqual(code, 410)
        self.assertFalse(data["ok"])
        self.assertEqual(data["reason"], "deprecated_use_task_scheduler")

    def test_start_scheduler_is_noop(self) -> None:
        scheduler.start_scheduler()
        self.assertFalse(scheduler.is_running())


if __name__ == "__main__":
    unittest.main()
