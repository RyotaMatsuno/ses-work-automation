"""
test_mock_patterns.py - パターンA/B/Cのモック統合テスト
IMAP / Claude API / Notion / Playwright をモックしてパイプラインを検証する。
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE_DIR = Path(__file__).resolve().parent
SES_WORK = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(SES_WORK))

SAMPLE_TEXT_A = (
    "氏名: 田中太郎\n所属: テックソリューション株式会社\n"
    "経験年数: 5年\n希望単価: 65万円\n稼働可能: 即日\n"
    "スキル: Java, Spring, Oracle, Linux, AWS\n" * 30
)

SAMPLE_TEXT_B = (
    "氏名: 佐藤花子\n所属: ABCパートナーズ\n"
    "経験年数: 3年\n希望単価: 55万円\n稼働可能: 2026-07-01\n"
    "スキル: Python, Django, PostgreSQL\n" * 20
)

SAMPLE_TEXT_C = (
    "氏名: 山田一郎\n所属: XYZ商事\n経験年数: 8年\n希望単価: 75万円\n"
    "氏名: 鈴木二郎\n所属: XYZ商事\n経験年数: 4年\n希望単価: 60万円\n"
    "氏名: 高橋三郎\n所属: DEF技研\n経験年数: 6年\n希望単価: 70万円\n" * 15
)

META = {
    "subject": "【テスト】スキルシート送付",
    "from": "hr@techsolution.co.jp",
    "date": "2026-06-09",
    "account": "sessales",
}


class MockPatternTests(unittest.TestCase):
    def setUp(self):
        self.register_calls = []

        def _register(engineer, meta):
            self.register_calls.append({"engineer": engineer, "meta": meta})
            return True

        self.register_patcher = patch(
            "utils.notion_writer.register_engineer",
            side_effect=_register,
        )
        self.mock_register = self.register_patcher.start()

    def tearDown(self):
        self.register_patcher.stop()

    def test_pattern_a_attachment(self):
        """パターンA: 添付Excel/PDF/Word → エンジニア抽出 → Notion登録"""
        from importer import process_attachments

        engineer = {
            "name": "田中太郎",
            "affiliation": "テックソリューション株式会社",
            "price": 65,
            "available_date": "2026-06-09",
            "experience_years": 5,
            "skills": ["Java", "Spring", "Oracle"],
        }

        with (
            patch("parsers.file_parser.parse_file", return_value=SAMPLE_TEXT_A),
            patch("ai_extractor.classify_content", return_value="engineer"),
            patch("ai_extractor.extract_engineers", return_value=[engineer]),
        ):
            stats = process_attachments(
                [{"filename": "skillsheet.xlsx", "ext": ".xlsx", "data": b"dummy"}],
                META,
            )

        self.assertEqual(stats["success"], 1)
        self.assertEqual(stats["error"], 0)
        self.assertEqual(len(self.register_calls), 1)
        self.assertEqual(self.register_calls[0]["engineer"]["name"], "田中太郎")

    def test_pattern_b_single_sheet(self):
        """パターンB: Google Spreadsheet URL（1人分）→ Notion登録"""
        from importer import process_sheet_urls

        engineer = {
            "name": "佐藤花子",
            "affiliation": "ABCパートナーズ",
            "price": 55,
            "available_date": "2026-07-01",
            "experience_years": 3,
            "skills": ["Python", "PostgreSQL"],
        }
        sheet_url = "https://docs.google.com/spreadsheets/d/abc123/edit"

        with (
            patch(
                "sheet_fetcher.fetch_sheet_text",
                return_value={"status": "ok", "text": SAMPLE_TEXT_B},
            ),
            patch("ai_extractor.extract_engineers", return_value=[engineer]),
        ):
            stats = process_sheet_urls([sheet_url], META)

        self.assertEqual(stats["success"], 1)
        self.assertEqual(len(self.register_calls), 1)
        self.assertEqual(self.register_calls[0]["engineer"]["name"], "佐藤花子")

    def test_pattern_c_multi_sheet(self):
        """パターンC: Google Spreadsheet URL（複数人リスト）→ 一括登録"""
        from importer import process_sheet_urls

        engineers = [
            {"name": "山田一郎", "affiliation": "XYZ商事", "price": 75, "skills": ["Java"]},
            {"name": "鈴木二郎", "affiliation": "XYZ商事", "price": 60, "skills": ["Python"]},
            {"name": "高橋三郎", "affiliation": "DEF技研", "price": 70, "skills": ["AWS"]},
        ]
        sheet_url = "https://docs.google.com/spreadsheets/d/multi456/edit"

        with (
            patch(
                "sheet_fetcher.fetch_sheet_text",
                return_value={"status": "ok", "text": SAMPLE_TEXT_C},
            ),
            patch("ai_extractor.extract_engineers", return_value=engineers),
        ):
            stats = process_sheet_urls([sheet_url], META)

        self.assertEqual(stats["success"], 3)
        self.assertEqual(len(self.register_calls), 3)
        names = [c["engineer"]["name"] for c in self.register_calls]
        self.assertEqual(names, ["山田一郎", "鈴木二郎", "高橋三郎"])

    def test_sheet_login_required_skipped(self):
        """ログイン必要スプレッドシートはスキップ"""
        from importer import process_sheet_urls

        with patch(
            "sheet_fetcher.fetch_sheet_text",
            return_value={"status": "login_required"},
        ):
            stats = process_sheet_urls(
                ["https://docs.google.com/spreadsheets/d/private/edit"],
                META,
            )

        self.assertEqual(stats["skip"], 1)
        self.assertEqual(len(self.register_calls), 0)

    def test_notion_upsert_by_name_and_affiliation(self):
        """名前+所属で既存レコードを検索する"""
        from utils.notion_writer import find_engineer_page_id

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "page-abc",
                    "properties": {
                        "所属会社名": {
                            "type": "rich_text",
                            "rich_text": [{"plain_text": "テックソリューション"}],
                        }
                    },
                },
                {
                    "id": "page-xyz",
                    "properties": {
                        "所属会社名": {
                            "type": "rich_text",
                            "rich_text": [{"plain_text": "別会社"}],
                        }
                    },
                },
            ]
        }

        with patch("utils.notion_writer.requests.post", return_value=mock_response):
            page_id = find_engineer_page_id("田中太郎", "テックソリューション")

        self.assertEqual(page_id, "page-abc")

    def test_costguard_blocks_llm(self):
        """CostGuard上限時はLLM呼び出しをスキップ"""
        from ai_extractor import extract_engineers

        with patch("ai_extractor.can_spend", return_value=False):
            result = extract_engineers(SAMPLE_TEXT_A, "test.xlsx")

        self.assertEqual(result, [])


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(MockPatternTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
