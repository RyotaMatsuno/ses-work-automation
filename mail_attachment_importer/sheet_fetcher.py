"""Google Spreadsheet text fetcher (re-export from common)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from common.sheet_fetcher import fetch_sheet_text

__all__ = ["fetch_sheet_text"]
