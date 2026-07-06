"""勤務地抽出モジュール。メール本文から勤務地を取得する。"""
from __future__ import annotations

import re

LOCATION_PATTERNS = [
    r'【(?:勤務地|場所|エリア)】\s*(.+?)(?:\n|$)',
    r'(?:勤務地|就業場所|勤務場所|場所|エリア|勤務先|最寄り駅)[：:\s]*(.+?)(?:\n|$)',
]

REMOTE_KEYWORDS = ['リモート', 'テレワーク', 'フルリモート', '在宅']

_COMPILED = [re.compile(p, re.MULTILINE) for p in LOCATION_PATTERNS]


def extract_location(body: str) -> str | None:
    """本文から勤務地を抽出。見つからない場合 None。"""
    if not body:
        return None
    for pat in _COMPILED:
        m = pat.search(body)
        if m:
            loc = m.group(1).strip()
            loc = re.sub(r'[（(].*?[)）]', '', loc).strip()
            loc = re.sub(r'[\s　]+', ' ', loc).strip()
            if 2 <= len(loc) <= 30:
                return loc
    for kw in REMOTE_KEYWORDS:
        if kw in body:
            return 'リモート'
    return None
