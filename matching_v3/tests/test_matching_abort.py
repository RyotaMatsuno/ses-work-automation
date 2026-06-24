from __future__ import annotations

from unittest.mock import MagicMock, patch

import matching_v3


def test_run_live_aborts_when_active_engineers_filter_fails():
    notion = MagicMock()
    notion.get_new_cases.return_value = []
    notion.get_active_engineers.side_effect = RuntimeError("提案対象フラグフィルタ利用不可のためマッチング中断")

    with (
        patch("flag_auto_updater.run_flag_updater.run_flag_updater", return_value=0),
        patch("matching_v3.NotionClient", return_value=notion),
        patch("matching_v3._notify_matching_abort") as notify,
        patch("matching_v3.ProcessedDB"),
        patch("matching_v3.CostGuard"),
        patch("matching_v3.Notifier"),
        patch("matching_v3.SkillNormalizer"),
    ):
        matching_v3._run_live()

    notify.assert_called_once()
    assert "マッチング中断" in notify.call_args.args[0]
