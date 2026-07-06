"""Station extractor — extracts nearest station from engineer text."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from engineer_extractor.engineer_text_parser import ParsedEngineerText


@dataclass
class StationResult:
    station: str | None = None
    line: str | None = None
    area: str | None = None
    confidence: float = 0.0
    source: str = "none"


_STATION_SUFFIX = r"(?:駅|ステーション)"
_LINE_PREFIX = r"(?:[^\s　。、\n]{2,10}線|JR[^\s　。、\n]{0,8}|[^\s　。、\n]{2,8}鉄道)"

_STATION_LABEL = r"(?:最寄り駅|最寄駅)"
_LABELED_STATION_RE = re.compile(
    _STATION_LABEL + r"[:：\s]*(?:(" + _LINE_PREFIX + r")\s+)?([^\s　。、\n]{1,15}" + _STATION_SUFFIX + r")"
)
_LABELED_STATION_PLAIN_RE = re.compile(
    _STATION_LABEL + r"[:：\s]*(?:(" + _LINE_PREFIX + r")\s+)?([^、。\s　\n]{2,10})(?=[、。.\s　\n]|$)"
)
_SUBJECT_PIPE_RE = re.compile(
    r"[｜|]([^\s　。、\n|｜]{1,10}" + _STATION_SUFFIX + r")"
)
_BODY_STATION_RE = re.compile(
    _STATION_LABEL + r"[:：は]?\s*(?:(" + _LINE_PREFIX + r")\s+)?([^\s　。、\n]{1,15}" + _STATION_SUFFIX + r")"
)
_BODY_STATION_PLAIN_RE = re.compile(
    _STATION_LABEL + r"[:：は]?\s*(?:(" + _LINE_PREFIX + r")\s+)?([^、。\s　\n]{2,10})(?=[、。.\s　\n]|$)"
)
# 広域body検索: ラベルなしで「○○駅」または「○○駅付近/近く」を捕捉
_BODY_STATION_BROAD_RE = re.compile(
    r"([^\s　。、\n「」『』【】（）()]{1,15}" + _STATION_SUFFIX + r")(?:付近|近く|より|から|にて)?"
)

# prefecture/area keywords
_PREF_RE = re.compile(
    r"(東京|神奈川|埼玉|千葉|大阪|愛知|福岡|北海道|宮城|広島|京都|兵庫|静岡|茨城|栃木|群馬|新潟|長野|岐阜|三重|滋賀|奈良|和歌山|岡山|広島|山口|徳島|香川|愛媛|高知|福岡|佐賀|長崎|熊本|大分|宮崎|鹿児島|沖縄)(?:都|道|府|県)?"
)


def _clean_station(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"[（(][^)）]*[)）]$", "", raw).strip()
    # 路線名プレフィックス除去: 「JR常磐線金町駅」→「金町駅」
    line_tail = re.search(r"([^線\s　]{2,10}駅)$", raw)
    if line_tail:
        raw = line_tail.group(1)
    # ノイズプレフィックス除去: 「48歳_女性_護国寺駅」→「護国寺駅」
    noise_tail = re.search(r"([^\s　。、\n「」『』【】（）()_]{2,10}駅)$", raw)
    if noise_tail:
        raw = noise_tail.group(1)
    if raw and not raw.endswith(("駅", "ステーション")):
        raw = f"{raw}駅"
    return raw


def _is_valid_station(station: str) -> bool:
    if not station or len(station) < 3:
        return False
    if station in {"り駅", "寄駅", "最寄駅", "最寄り駅", "駅"}:
        return False
    if re.search(r"\d歳|男性|女性|_", station):
        return False
    return True


def _station_from_match(
    line: str | None,
    station: str,
    *,
    text: str,
    confidence: float,
    source: str,
) -> StationResult | None:
    station = _clean_station(station)
    if not _is_valid_station(station):
        return None
    return StationResult(
        station=station,
        line=line,
        area=_extract_area(text),
        confidence=confidence,
        source=source,
    )


def extract_station(parsed: ParsedEngineerText) -> StationResult:
    # Layer 1: labeled_fields
    for key in ("最寄", "最寄り駅", "最寄駅"):
        if key in parsed.labeled_fields:
            text = parsed.labeled_fields[key]
            m = _LABELED_STATION_RE.search(text)
            if m:
                result = _station_from_match(
                    m.group(1), m.group(2), text=text, confidence=0.95, source="labeled"
                )
                if result:
                    return result
            m = _LABELED_STATION_PLAIN_RE.search(text)
            if m:
                result = _station_from_match(
                    m.group(1), m.group(2), text=text, confidence=0.90, source="labeled"
                )
                if result:
                    return result
            # fallback: the whole field value might just be a station name
            candidate = text.strip()
            if re.search(_STATION_SUFFIX, candidate):
                return StationResult(
                    station=_clean_station(candidate),
                    confidence=0.90, source="labeled"
                )

    # Layer 2: body explicit mention
    search_text = parsed.body or parsed.full_text
    m = _BODY_STATION_RE.search(search_text)
    if m:
        result = _station_from_match(
            m.group(1), m.group(2), text=search_text, confidence=0.85, source="body"
        )
        if result:
            return result
    m = _BODY_STATION_PLAIN_RE.search(search_text)
    if m:
        result = _station_from_match(
            m.group(1), m.group(2), text=search_text, confidence=0.82, source="body"
        )
        if result:
            return result

    # Layer 3: subject pipe-separated
    if parsed.subject:
        m = _SUBJECT_PIPE_RE.search(parsed.subject)
        if m:
            station = _clean_station(m.group(1))
            if _is_valid_station(station):
                return StationResult(
                    station=station,
                    confidence=0.80, source="subject"
                )

    # Layer 4: broad body scan for 「○○駅」（誤検知抑制のため信頼度低め）
    _NOISE_STATION = re.compile(r"^(?:各駅|終点|乗換|直通|始発|急行|特急|新幹線|通勤|改札)")
    for text_src in (search_text, parsed.full_text):
        for m in _BODY_STATION_BROAD_RE.finditer(text_src):
            candidate = _clean_station(m.group(1))
            if not _is_valid_station(candidate):
                continue
            if _NOISE_STATION.match(candidate):
                continue
            return StationResult(
                station=candidate,
                confidence=0.65, source="body_broad"
            )

    return StationResult(confidence=0.0, source="none")


def _extract_area(text: str) -> str | None:
    m = _PREF_RE.search(text)
    return m.group(0) if m else None
