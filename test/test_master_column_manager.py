"""master_column_manager のユニットテスト（モック使用）。"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
SHEETS_DIR = ROOT / "sheets"
sys.path.insert(0, str(SHEETS_DIR))

import master_column_manager as mcm


def test_kado_column_name():
    assert mcm.kado_column_name(2026, 7) == "2026年7月_稼働確定"


def test_guard_write_blocks_dry_run():
    assert mcm._guard_write(False, "test") is False


def test_guard_write_blocks_without_env(monkeypatch):
    monkeypatch.delenv("SHEETS_WRITE_APPROVED", raising=False)
    assert mcm._guard_write(True, "test") is False


def test_guard_write_allows_with_env(monkeypatch):
    monkeypatch.setenv("SHEETS_WRITE_APPROVED", "1")
    assert mcm._guard_write(True, "test") is True


def test_add_monthly_column_idempotent():
    service = MagicMock()
    terra = [[], [], [], ["h", "2026年7月_稼働確定"], ["", "田中"]]
    ft = [[], [], ["h", "2026年7月_稼働確定"], ["", "山田"]]
    gl = [[], [], ["h", "2026年7月_稼働確定"], ["", "石崎"]]
    sheets = {"TERRA": terra, "フラップテック": ft, "グレイスライン": gl}

    with (
        patch.object(mcm, "get_sheets_service", return_value=service),
        patch.object(mcm, "_read_sheet", side_effect=lambda _s, tab: sheets[tab]),
        patch.object(mcm, "_append_column_end") as append,
        patch.object(mcm, "_guard_write", return_value=True),
    ):
        added = mcm.add_monthly_column("2026-07", execute=True)
    assert added is False
    append.assert_not_called()


def test_add_monthly_column_dry_run_never_appends():
    service = MagicMock()
    existing = [["担当", "氏名"], ["", "田中"]]
    with (
        patch.object(mcm, "get_sheets_service", return_value=service),
        patch.object(mcm, "_read_sheet", return_value=existing),
        patch.object(mcm, "_retry") as retry,
    ):
        added = mcm.add_monthly_column("2026-07", execute=False)
    assert added is True
    retry.assert_not_called()


def test_ensure_keiyaku_kubun_is_noop():
    assert mcm.ensure_keiyaku_kubun_column(execute=True) is False


def test_ensure_notion_name_is_noop():
    assert mcm.ensure_notion_name_column(execute=True) is False


def test_populate_active_status_by_dates():
    people = [
        mcm.PersonRow("TERRA", 5, "田中", date(2026, 1, 1), None),
        mcm.PersonRow("TERRA", 6, "佐藤", date(2026, 8, 1), None),
        mcm.PersonRow("TERRA", 7, "鈴木", None, None),
    ]
    with (
        patch.object(mcm, "get_sheets_service", return_value=MagicMock()),
        patch.object(mcm, "_collect_person_rows", return_value=people),
        patch.object(mcm, "_write_cells") as write_cells,
    ):
        summary = mcm.populate_active_status("2026-07", execute=False)
    assert summary["counts"]["TRUE"] == 1
    assert summary["counts"]["FALSE"] == 1
    assert summary["counts"]["skip"] == 1
    write_cells.assert_not_called()


def test_clear_terra_kubun_dry_run():
    terra_data = [
        ["h1"],
        ["h2"],
        ["h3"],
        ["担当", "区分", "ステータス", "氏名", "契約区分"],
        ["", "P", "稼働中", "田中", "業務委託料"],
        ["", "BP", "稼働中", "山田", "通常"],
    ]
    with (
        patch.object(mcm, "get_sheets_service", return_value=MagicMock()),
        patch.object(mcm, "_read_sheet", return_value=terra_data),
        patch.object(mcm, "_write_cells") as write_cells,
    ):
        result = mcm.clear_terra_kubun(execute=False)
    assert result["before"] == 1
    assert result["cleared"] == 0
    write_cells.assert_not_called()


def _function_source_chunk(source: str, fn_name: str, size: int = 2500) -> str:
    pattern = f"def {fn_name}"
    start = source.find(pattern)
    assert start != -1, f"{fn_name} not found"
    return source[start : start + size]


def test_all_write_paths_use_guard():
    source = (SHEETS_DIR / "master_column_manager.py").read_text(encoding="utf-8")
    for fn_name in ("_append_column_at", "_write_cells"):
        chunk = _function_source_chunk(source, fn_name)
        assert "_guard_write" in chunk, f"{fn_name} must call _guard_write"

    chunk = _function_source_chunk(source, "populate_active_status", size=5000)
    assert "_guard_write" in chunk
    assert "_write_cells" in chunk

    chunk = _function_source_chunk(source, "clear_terra_kubun", size=3000)
    assert "_write_cells" in chunk


def test_execute_without_env_var_blocks_write(monkeypatch):
    monkeypatch.delenv("SHEETS_WRITE_APPROVED", raising=False)
    service = MagicMock()
    terra_header = [["h1"], ["h2"], ["h3"], ["担当", "ステータス", "氏名"]]
    with patch.object(mcm, "_read_sheet", return_value=terra_header), patch.object(mcm, "_retry") as retry:
        result = mcm._append_column_at(service, "TERRA", "テスト列", 5, execute=True)
    assert result is False
    retry.assert_not_called()


def test_dry_run_default_does_not_write():
    script = SHEETS_DIR / "master_column_manager.py"
    runner = f"""
import sys
from unittest.mock import MagicMock, patch
sys.path.insert(0, {str(SHEETS_DIR)!r})
import master_column_manager as mcm

with patch.object(mcm, "get_sheets_service") as gs, \\
     patch.object(mcm, "_collect_person_rows", return_value=[]), \\
     patch.object(mcm, "_read_sheet", return_value=[["氏名"]]), \\
     patch.object(mcm, "_retry") as retry:
    gs.return_value = MagicMock()
    sys.argv = [{str(script)!r}, "2026-07"]
    mcm.main()
    assert not retry.called
"""
    env = {**os.environ, "PYTHONPATH": str(SHEETS_DIR)}
    result = subprocess.run(
        [sys.executable, "-c", runner],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr or result.stdout
