"""Rule-based work location extraction from SES project text."""

from __future__ import annotations

import re
from dataclasses import dataclass

LOCATION_PATTERNS = [
    re.compile(r"【(?:勤務地|場所|エリア)】\s*(.+?)(?:\n|$)", re.MULTILINE),
    re.compile(
        r"(?:勤務地|就業場所|勤務場所|場所|エリア|勤務先|最寄り駅)[：:\s]*(.+?)(?:\n|$)",
        re.MULTILINE,
    ),
]

STATION_PATTERN = re.compile(r"([^\s　]+駅)")
PREF_PATTERN = re.compile(
    r"(東京都|神奈川県|埼玉県|千葉県|大阪府|京都府|兵庫県|愛知県|福岡県|北海道|"
    r"首都圏|都内|関西|関東)"
)
REMOTE_ONLY = re.compile(r"^(リモート|テレワーク|在宅|フルリモート)$")


@dataclass
class LocationResult:
    location: str | None = None
    station: str | None = None
    area: str | None = None
    confidence: float = 0.0
    method: str = "regex"
    evidence: str | None = None


def _normalize_location(raw: str) -> str:
    loc = re.sub(r"[（(].*?[)）]", "", raw).strip()
    loc = re.sub(r"[\s　]+", " ", loc).strip()
    return loc


def extract_location(text: str) -> LocationResult:
    """Extract normalized work location from text."""
    if not text or not text.strip():
        return LocationResult(confidence=0.0)

    for pattern in LOCATION_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        loc = _normalize_location(match.group(1))
        if len(loc) < 2 or len(loc) > 30:
            continue
        if REMOTE_ONLY.match(loc):
            return LocationResult(confidence=0.4, evidence=match.group(0))
        station_match = STATION_PATTERN.search(loc)
        area_match = PREF_PATTERN.search(loc)
        return LocationResult(
            location=loc,
            station=station_match.group(1) if station_match else None,
            area=area_match.group(1) if area_match else None,
            confidence=0.9,
            method="regex",
            evidence=match.group(0).strip(),
        )

    return LocationResult(confidence=0.0)
