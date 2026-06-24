from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

JST = timezone(timedelta(hours=9))
MAX_PER_DAY = 20
_LOG_ROOT = Path(__file__).resolve().parent.parent / "logs" / "failure_samples"


def _today_path() -> Path:
    day = datetime.now(JST).date().isoformat()
    _LOG_ROOT.mkdir(parents=True, exist_ok=True)
    return _LOG_ROOT / f"{day}.jsonl"


def _count_today(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def collect_failure(category: str, data: dict[str, Any], reason: str) -> bool:
    """失敗サンプルを日次JSONLに追記。1日20件上限。収集できたら True。"""
    path = _today_path()
    if _count_today(path) >= MAX_PER_DAY:
        return False
    row = {
        "ts": datetime.now(JST).isoformat(),
        "category": category,
        "reason": reason,
        "data": data,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return True
