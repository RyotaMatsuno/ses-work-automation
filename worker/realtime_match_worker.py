#!/usr/bin/env python3
"""ses_work/worker 互換エントリ（matching_v3 実装へ委譲）。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_TARGET = Path(__file__).resolve().parent.parent / "matching_v3" / "worker" / "realtime_match_worker.py"
_SPEC = importlib.util.spec_from_file_location("realtime_match_worker", _TARGET)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[__name__] = _MODULE
_SPEC.loader.exec_module(_MODULE)

for _name in dir(_MODULE):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_MODULE, _name)
# tests / 外部参照用
for _name in ("_today_key", "_case_within_window", "JST", "run_once", "main"):
    globals()[_name] = getattr(_MODULE, _name)

if __name__ == "__main__":
    raise SystemExit(_MODULE.main())
