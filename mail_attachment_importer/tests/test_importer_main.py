from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def _sample_mail(uid: str, subject: str = "テスト件名") -> dict:
    return {
        "uid": uid,
        "subject": subject,
        "from": "test@example.com",
        "date": "2026-06-19",
        "account": "sessales",
        "attachments": [{"filename": "skillsheet.xlsx", "ext": ".xlsx", "data": b"dummy"}],
        "sheet_urls": [],
        "project_sheet_urls": [],
    }


class ImporterMainTests(unittest.TestCase):
    @patch("mail_fetcher.save_processed_id")
    @patch("mail_fetcher.fetch_new_emails")
    def test_main_continues_after_single_mail_failure(self, mock_fetch, mock_mark):
        from importer import main

        mock_fetch.return_value = [
            _sample_mail("uid-1"),
            _sample_mail("uid-2"),
        ]

        with patch(
            "importer.process_attachments", side_effect=[RuntimeError("boom"), {"success": 0, "skip": 0, "error": 0}]
        ):
            exit_code = main()

        self.assertEqual(exit_code, 1)
        self.assertEqual(mock_mark.call_count, 1)
        mock_mark.assert_called_with("uid-2", "sessales")

    @patch("mail_fetcher.fetch_new_emails", return_value=[])
    def test_main_returns_zero_when_no_emails(self, _mock_fetch):
        from importer import main

        self.assertEqual(main(), 0)

    @patch("mail_fetcher.fetch_new_emails", side_effect=RuntimeError("fetch failed"))
    def test_main_returns_one_on_fetch_failure(self, _mock_fetch):
        from importer import main

        self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
