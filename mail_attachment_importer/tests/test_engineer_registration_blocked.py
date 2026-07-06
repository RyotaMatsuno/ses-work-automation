from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

SAMPLE_TEXT = (
    "氏名: 田中太郎\n所属: テックソリューション株式会社\n"
    "経験年数: 5年\n希望単価: 65万円\n稼働可能: 即日\n"
    "スキル: Java, Spring, Oracle, Linux, AWS\n" * 30
)

META = {
    "subject": "【テスト】スキルシート送付",
    "from": "hr@techsolution.co.jp",
    "date": "2026-06-09",
    "account": "sessales",
}


class EngineerRegistrationBlockedTests(unittest.TestCase):
    @patch("utils.notion_writer.register_engineer")
    @patch("utils.notion_writer.register_project")
    def test_engineer_attachment_is_skipped(self, mock_register_project, mock_register_engineer):
        from importer import process_attachments

        with (
            patch("parsers.file_parser.parse_file", return_value=SAMPLE_TEXT),
            patch("ai_extractor.classify_content", return_value="engineer"),
            patch("ai_extractor.extract_engineers") as mock_extract,
        ):
            stats = process_attachments(
                [{"filename": "skillsheet.xlsx", "ext": ".xlsx", "data": b"dummy"}],
                META,
            )

        self.assertEqual(stats, {"success": 0, "skip": 1, "error": 0})
        mock_extract.assert_not_called()
        mock_register_engineer.assert_not_called()
        mock_register_project.assert_not_called()

    @patch("utils.notion_writer.register_engineer")
    @patch("utils.notion_writer.register_project", return_value=True)
    def test_project_attachment_still_registers(self, mock_register_project, mock_register_engineer):
        from importer import process_attachments

        project = {
            "title": "Java開発案件",
            "required_skills": ["Java"],
            "price_max": 70,
        }

        with (
            patch("parsers.file_parser.parse_file", return_value=SAMPLE_TEXT),
            patch("ai_extractor.classify_content", return_value="project"),
            patch("ai_extractor.extract_projects", return_value=[project]),
        ):
            stats = process_attachments(
                [{"filename": "project.xlsx", "ext": ".xlsx", "data": b"dummy"}],
                META,
            )

        self.assertEqual(stats, {"success": 1, "skip": 0, "error": 0})
        mock_register_engineer.assert_not_called()
        mock_register_project.assert_called_once()

    @patch("utils.notion_writer.register_engineer")
    def test_sheet_urls_are_all_skipped(self, mock_register_engineer):
        from importer import process_sheet_urls

        urls = [
            "https://docs.google.com/spreadsheets/d/abc123/edit",
            "https://docs.google.com/spreadsheets/d/def456/edit",
        ]
        stats = process_sheet_urls(urls, META)

        self.assertEqual(stats, {"success": 0, "skip": 2, "error": 0})
        mock_register_engineer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
