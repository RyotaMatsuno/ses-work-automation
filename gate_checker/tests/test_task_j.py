"""Task J/M: gate_checker v2.2 + Sonnet差替えのテスト。"""

from __future__ import annotations

import sys
from pathlib import Path

GATE_CHECKER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GATE_CHECKER_DIR))

import gate_check


def test_daily_call_limit_is_30() -> None:
    assert gate_check.DAILY_CALL_LIMIT == 30


def test_system_prompts_include_costguard_note() -> None:
    note = gate_check.COSTGUARD_NOTE
    for prompt in (
        gate_check.REQUIREMENTS_SYSTEM,
        gate_check.DESIGN_SYSTEM,
        gate_check.IMPLEMENTATION_SYSTEM,
        gate_check.TEST_SYSTEM,
    ):
        assert "CostGuardはLLM API呼び出し" in prompt
        assert "Notion API" in prompt
        assert note.strip() in prompt


def test_notion_api_code_should_not_trigger_costguard_in_prompt() -> None:
    """プロンプト改善: Notion APIはCostGuard対象外と明記されている。"""
    sample_code = """
def sync_notion():
    client = NotionClient()
    client.update_page(page_id, properties)
"""
    prompt = gate_check.IMPLEMENTATION_SYSTEM
    assert "非LLM外部APIはCostGuard対象外" in prompt
    assert "Notion DBへの読み書き" in prompt
    assert sample_code  # 参照用（実行確認）
