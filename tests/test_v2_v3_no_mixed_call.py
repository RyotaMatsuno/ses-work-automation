"""8.15 matching_v2 を直接呼ぶ箇所が matching_v3 に残っていないことを確認。"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
MATCHING_V3_DIR = BASE_DIR / "matching_v3"


def _get_python_files(directory: Path) -> list[Path]:
    return list(directory.glob("*.py"))


def test_no_matching_v2_import_in_matching_v3():
    """matching_v3 の Python ファイルが matching_v2 を import していないこと。"""
    offenders = []
    for py_file in _get_python_files(MATCHING_V3_DIR):
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = ""
                if isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                if "matching_v2" in module:
                    offenders.append((py_file.name, module))

    assert offenders == [], f"Found matching_v2 imports in matching_v3: {offenders}"


def test_matching_v3_skill_judge_uses_cost_guard():
    """matching_v3/skill_judge.py が cost_guard を経由していること。"""
    skill_judge = MATCHING_V3_DIR / "skill_judge.py"
    if not skill_judge.exists():
        pytest.skip("skill_judge.py not found")

    source = skill_judge.read_text(encoding="utf-8")
    assert "cost_guard" in source or "cg_allowed" in source, "skill_judge.py should use cost_guard"
