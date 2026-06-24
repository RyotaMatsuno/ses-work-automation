from __future__ import annotations

from unittest.mock import MagicMock, patch

import estimate_engineer_attrs as module


def test_run_estimate_logs_llm_decision_for_review_cases(capsys):
    engineers = [
        {
            "id": "page-1",
            "名前": "不明",
            "備考（LINEメモ）": "最寄り: 渋谷駅、Java/Spring",
            "properties": {"国籍": None, "居住地": "東京"},
        },
        {
            "id": "page-2",
            "名前": "BH0023",
            "備考（LINEメモ）": "",
            "properties": {"国籍": None, "居住地": None},
        },
    ]
    client = MagicMock()
    client.get_all_engineers.return_value = engineers

    with (
        patch.object(module, "FlagNotionClient", return_value=client),
        patch.object(
            module,
            "estimate_nationality_llm",
            side_effect=[
                ("日本", "LLM判定: 日本"),
                ("要確認", "判定材料なし"),
            ],
        ),
    ):
        result = module.run_estimate_engineer_attrs(dry_run=True)

    captured = capsys.readouterr()
    assert result == 0
    assert "[LLM判定]" in captured.out
    assert "BH0023" in captured.out and "判定材料なし" in captured.out
