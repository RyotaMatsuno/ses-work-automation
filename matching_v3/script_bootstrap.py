"""matching_v3 CLI スクリプト用の sys.path 初期化。"""
from __future__ import annotations

import sys
from pathlib import Path


def bootstrap() -> tuple[Path, Path]:
    matching_v3_dir = Path(__file__).resolve().parent
    ses_work = matching_v3_dir.parent
    if str(matching_v3_dir) not in sys.path:
        sys.path.insert(0, str(matching_v3_dir))
    if str(ses_work) not in sys.path:
        sys.path.insert(1, str(ses_work))
    return matching_v3_dir, ses_work
