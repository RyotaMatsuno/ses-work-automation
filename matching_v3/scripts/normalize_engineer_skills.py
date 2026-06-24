"""matching_v3 からの実行用ラッパー。本体は ses_work/scripts/normalize_engineer_skills.py。"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "normalize_engineer_skills.py"
sys.argv[0] = str(_SCRIPT)
runpy.run_path(str(_SCRIPT), run_name="__main__")
