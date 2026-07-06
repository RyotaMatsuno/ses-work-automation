"""Rule-based remote work style extraction from SES project text."""

from __future__ import annotations

import re
from dataclasses import dataclass

REMOTE_FULL = "full_remote"
REMOTE_HYBRID = "hybrid"
REMOTE_ONSITE = "onsite"
REMOTE_POSSIBLE = "remote_possible"
REMOTE_UNKNOWN = "unknown"

_FULL_REMOTE = re.compile(
    r"フルリモート|完全リモート|フル在宅|在宅100|出社なし|出社不要"
)
_PERIODIC_ONSITE = re.compile(
    r"週(\d+)出社|月(\d+)回出社|必要時出社|月1出社|リモート併用|ハイブリッド|一部出社|基本リモート"
)
_ONSITE = re.compile(r"常駐|オンサイト|出社前提|基本出社|フル出社|出社必須")
_REMOTE_POSSIBLE = re.compile(r"リモート|テレワーク|在宅")
_TEMPORARY_ONSITE = re.compile(
    r"初日出社|初月出社|立ち上がり.{0,8}出社|参画初日出社|"
    r"初回出社|初日のみ出社|入場初日出社|"
    r"セットアップ時出社|PC受取.{0,20}出社|貸与物受取.{0,20}出社"
)


@dataclass
class RemoteResult:
    remote_type: str = REMOTE_UNKNOWN
    onsite_days_per_week: int | None = None
    initial_onsite: bool | None = None
    initial_onsite_required: bool = False
    confidence: float = 0.0
    method: str = "regex"
    evidence: str | None = None
    needs_llm_fallback: bool = False


def _apply_initial_onsite(result: RemoteResult, text: str) -> RemoteResult:
    temp_match = _TEMPORARY_ONSITE.search(text)
    if temp_match:
        result.initial_onsite_required = True
        result.initial_onsite = True
    return result


def _parse_onsite_days(match: re.Match[str]) -> int | None:
    for i in range(1, (match.lastindex or 0) + 1):
        g = match.group(i)
        if g and g.isdigit():
            return int(g)
    if "月1出社" in match.group(0):
        return 1
    return None


def _apply_periodic_override(result: RemoteResult, text: str) -> RemoteResult:
    periodic = _PERIODIC_ONSITE.search(text)
    if not periodic:
        return result
    result.remote_type = REMOTE_HYBRID
    result.onsite_days_per_week = _parse_onsite_days(periodic)
    result.confidence = max(result.confidence, 0.85)
    result.evidence = periodic.group(0)
    return result


def extract_remote(text: str) -> RemoteResult:
    """Extract remote work classification from text."""
    if not text or not text.strip():
        return RemoteResult(remote_type=REMOTE_UNKNOWN, confidence=0.0)

    full_match = _FULL_REMOTE.search(text)
    onsite_match = _ONSITE.search(text)
    if full_match and onsite_match:
        result = RemoteResult(
            remote_type=REMOTE_UNKNOWN,
            confidence=0.2,
            evidence=f"{full_match.group(0)} / {onsite_match.group(0)}",
            needs_llm_fallback=True,
        )
        return _apply_initial_onsite(result, text)

    if full_match:
        result = RemoteResult(
            remote_type=REMOTE_FULL,
            confidence=0.9,
            method="regex",
            evidence=full_match.group(0),
        )
        result = _apply_initial_onsite(result, text)
        return _apply_periodic_override(result, text)

    periodic = _PERIODIC_ONSITE.search(text)
    if periodic:
        result = RemoteResult(
            remote_type=REMOTE_HYBRID,
            onsite_days_per_week=_parse_onsite_days(periodic),
            confidence=0.85,
            method="regex",
            evidence=periodic.group(0),
        )
        return _apply_initial_onsite(result, text)

    if onsite_match:
        result = RemoteResult(
            remote_type=REMOTE_ONSITE,
            confidence=0.85,
            method="regex",
            evidence=onsite_match.group(0),
        )
        return _apply_initial_onsite(result, text)

    remote_match = _REMOTE_POSSIBLE.search(text)
    if remote_match:
        result = RemoteResult(
            remote_type=REMOTE_POSSIBLE,
            confidence=0.6,
            method="regex",
            evidence=remote_match.group(0),
        )
        return _apply_initial_onsite(result, text)

    result = RemoteResult(remote_type=REMOTE_UNKNOWN, confidence=0.3)
    return _apply_initial_onsite(result, text)
