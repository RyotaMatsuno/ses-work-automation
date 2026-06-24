from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

KANTO_NAMES = {
    "東京都",
    "東京",
    "神奈川県",
    "神奈川",
    "埼玉県",
    "埼玉",
    "千葉県",
    "千葉",
    "茨城県",
    "茨城",
    "栃木県",
    "栃木",
    "群馬県",
    "群馬",
}

ALL_PREFECTURES = [
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
]

PREFECTURE_ALIASES = {
    pref.replace("都", "").replace("府", "").replace("県", ""): pref
    for pref in ALL_PREFECTURES
    if pref not in ("北海道", "京都府")
}
PREFECTURE_ALIASES["北海道"] = "北海道"

VAGUE_START_DATES = {"即日", "即時", "随時", "応相談", "確認中"}

FOREIGN_KEYWORDS = (
    "外国籍",
    "外国籍候補",
    "日本語N1",
    "永住者",
    "帰化",
    "国籍不問",
    "外国籍NG",
)

KANTO_EXCEPTION_KEYWORDS = (
    "フルリモート可",
    "関東常駐可",
    "関東出社可",
    "引越し予定",
)

ENGINEER_PROPERTY_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "単価": ("単価", "単価（万円）"),  # canonical=円。単価（万円）のみ存在時は×10000換算
    "提案対象フラグ": ("提案対象フラグ",),
    "備考": ("備考", "備考（LINEメモ）"),
    "情報取得日": ("情報取得日",),
    "氏名": ("氏名", "名前"),
    "スキル": ("スキル",),
    "稼働開始日": ("稼働開始日", "稼働可能日"),
}


@dataclass
class ValidationResult:
    status: str  # "OK" | "REVIEW" | "SKIP"
    proposal_target: bool = True
    reasons: list[str] = field(default_factory=list)
    remark_additions: list[str] = field(default_factory=list)


def resolve_engineer_property_names(db_properties: set[str]) -> dict[str, str]:
    """Notion DB上の実プロパティ名を canonical 名にマッピングする。"""
    resolved: dict[str, str] = {}
    for canonical, aliases in ENGINEER_PROPERTY_REQUIREMENTS.items():
        for alias in aliases:
            if alias in db_properties:
                resolved[canonical] = alias
                break
    return resolved


def price_field_unit(prop_name: str) -> str:
    """Notion上の単価プロパティ名から単位を返す。"""
    if prop_name == "単価":
        return "yen"
    return "man"


def describe_price_field(prop_map: dict[str, str]) -> str:
    field = prop_map.get("単価", "単価")
    if price_field_unit(field) == "yen":
        return f"単価フィールド: {field}（円単位）"
    return f"単価フィールド: {field}（万円）→円換算"


def missing_engineer_properties(db_properties: set[str]) -> list[str]:
    missing: list[str] = []
    for canonical, aliases in ENGINEER_PROPERTY_REQUIREMENTS.items():
        if not any(alias in db_properties for alias in aliases):
            missing.append(canonical)
    return missing


def _get_field(record: dict, *keys: str):
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return None


def _as_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_residence(value) -> str:
    text = _as_text(value)
    if not text:
        return ""
    pref = find_prefecture_from_text(text)
    return pref or text


def find_prefecture_from_text(text: str) -> str:
    if not text:
        return ""
    candidates: list[tuple[int, str]] = []
    for pref in ALL_PREFECTURES:
        pos = text.find(pref)
        if pos >= 0:
            candidates.append((pos, pref))
    for alias, pref in PREFECTURE_ALIASES.items():
        pos = text.find(alias)
        if pos >= 0:
            candidates.append((pos, pref))
    if not candidates:
        return ""
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _is_kanto_prefecture(prefecture: str) -> bool:
    if not prefecture:
        return True
    short = prefecture.replace("都", "").replace("府", "").replace("県", "")
    return (
        prefecture in KANTO_NAMES
        or short in KANTO_NAMES
        or prefecture.startswith("東京")
        or prefecture.startswith("神奈川")
        or prefecture.startswith("埼玉")
        or prefecture.startswith("千葉")
        or prefecture.startswith("茨城")
        or prefecture.startswith("栃木")
        or prefecture.startswith("群馬")
    )


def normalize_price_yen(value) -> int | None:
    """単価を円単位の整数に正規化する。判定不能は None。"""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if number < 0:
            return int(number)
        if number == 0:
            return 0
        if number >= 1000:
            return int(number)
        return int(number * 10000)

    text = _as_text(value)
    if not text:
        return None
    if text in ("応相談",):
        return None

    normalized = text.replace(",", "").replace("，", "")
    range_match = re.search(r"(\d+)\s*[〜~\-－]\s*(\d+)\s*万", normalized)
    if range_match:
        return int(range_match.group(1)) * 10000

    man_match = re.search(r"(\d+)\s*万", normalized)
    if man_match:
        return int(man_match.group(1)) * 10000

    digits = re.sub(r"[^\d]", "", normalized)
    if not digits:
        return None
    number = int(digits)
    if "万" in normalized and number < 1000:
        return number * 10000
    if number < 1000:
        return number * 10000
    return number


def normalize_available_date(value) -> str:
    text = _as_text(value)
    if not text:
        return ""
    if text in VAGUE_START_DATES:
        return text
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return text
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.date().isoformat()
    except ValueError:
        return text


def price_to_man_yen(yen_value: int | None) -> float | None:
    if yen_value is None:
        return None
    return yen_value / 10000


REMARK_APPEND_MAX_LEN = 1800


def append_remark(existing: str, additions: list[str], *, max_len: int = REMARK_APPEND_MAX_LEN) -> str:
    if not additions:
        return existing or ""
    base = existing or ""
    if len(base) > max_len:
        return base
    suffix = "\n".join(additions)
    if not base.strip():
        return suffix
    return f"{base.rstrip()}\n{suffix}"


def validate_engineer(record: dict) -> ValidationResult:
    """エンジニアレコードを検証し ValidationResult を返す。"""
    working = dict(record)
    reasons: list[str] = []
    remark_additions: list[str] = []
    proposal_target = True
    skip = False

    # ① 正規化（単価・稼働開始日・居住地）
    raw_price = _get_field(working, "単価", "price", "単価（万円）")
    normalized_price_yen = normalize_price_yen(raw_price)
    working["単価"] = normalized_price_yen
    working["単価（万円）"] = price_to_man_yen(normalized_price_yen)

    raw_start = _get_field(working, "稼働開始日", "available_date", "稼働可能日")
    normalized_start = normalize_available_date(raw_start)
    working["稼働開始日"] = normalized_start
    working["available_date"] = normalized_start

    raw_residence = _get_field(working, "居住地", "location", "residence", "station", "nearest_station")
    normalized_residence = _normalize_residence(raw_residence)
    working["居住地"] = normalized_residence

    # ② 氏名欠損 → SKIP
    name = _as_text(_get_field(working, "氏名", "name", "名前"))
    if not name or name in {"（名前未記載）", "不明", "未記載", "N/A", "n/a"}:
        reasons.append("氏名欠損")
        remark_additions.append("[validation] 氏名欠損")
        skip = True

    # ③ スキル欠損 → REVIEW
    skills = _get_field(working, "スキル", "skills") or []
    if not isinstance(skills, list):
        skills = [skills] if skills else []
    skills = [str(skill).strip() for skill in skills if str(skill).strip()]
    if not skills:
        proposal_target = False
        reasons.append("スキル欠損")
        remark_additions.append("[validation] スキル欠損")

    # ④ 稼働開始日欠損
    start_date = _as_text(working.get("稼働開始日"))
    if not start_date or start_date in VAGUE_START_DATES:
        proposal_target = False
        reasons.append("稼働開始日欠損または要確認")
        remark_additions.append("[validation] 稼働開始日欠損または要確認")

    # ⑤ 外国籍チェック
    nationality_text = " ".join(
        _as_text(_get_field(working, key))
        for key in ("国籍", "nationality", "備考", "備考（LINEメモ）", "note", "remark")
    )
    if any(keyword in nationality_text for keyword in FOREIGN_KEYWORDS):
        proposal_target = False
        reasons.append("外国籍関連キーワード検出")
        remark_additions.append("[validation] 外国籍関連キーワード検出")

    # ⑥ 地方チェック
    location_text = " ".join(
        _as_text(_get_field(working, key))
        for key in ("居住地", "location", "residence", "備考", "備考（LINEメモ）", "note", "remark")
    )
    prefecture = find_prefecture_from_text(location_text)
    if prefecture and not _is_kanto_prefecture(prefecture):
        if any(keyword in location_text for keyword in KANTO_EXCEPTION_KEYWORDS):
            reasons.append(f"関東圏外（{prefecture}）だが例外条件あり")
            remark_additions.append(f"[validation] 関東圏外（{prefecture}）だが例外条件あり")
        else:
            proposal_target = False
            reasons.append(f"関東圏外: {prefecture}")
            remark_additions.append(f"[validation] 関東圏外: {prefecture}")

    # ⑦ 単価チェック
    price_review = False
    if raw_price is not None and _as_text(raw_price) in ("応相談",):
        price_review = True
    if normalized_price_yen is None:
        price_review = True
    elif normalized_price_yen <= 0:
        price_review = True
    if price_review:
        proposal_target = False
        reasons.append("単価要確認")
        remark_additions.append("[validation] 単価要確認")

    # 優先順: SKIP > REVIEW > OK
    if skip:
        status = "SKIP"
    elif reasons:
        status = "REVIEW"
    else:
        status = "OK"

    return ValidationResult(
        status=status,
        proposal_target=proposal_target,
        reasons=reasons,
        remark_additions=remark_additions,
    )
