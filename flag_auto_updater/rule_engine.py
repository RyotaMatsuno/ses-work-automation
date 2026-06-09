from __future__ import annotations

from datetime import date, datetime

BLANK_DAYS_THRESHOLD = 365  # 1年以上をブランクとみなす
KANTO_PREFECTURES = ["東京", "神奈川", "埼玉", "千葉", "茨城", "栃木", "群馬"]


def extract_prop(engineer: dict, name: str, prop_type: str):
    """エンジニア dict からプロパティ値を安全に取得する。"""
    props = engineer.get("properties") or {}
    if name in props:
        return props.get(name)
    if name in engineer:
        return engineer.get(name)
    return None


def _parse_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _is_kanto(residence: str) -> bool:
    for prefecture in KANTO_PREFECTURES:
        if residence == prefecture or residence.startswith(prefecture):
            return True
    return False


def judge_engineer(engineer: dict, *, today: date | None = None) -> tuple[bool, list[str]]:
    """除外ルールを適用し (提案対象か, 除外理由リスト) を返す。"""
    reference = today or date.today()
    reasons: list[str] = []

    nationality = extract_prop(engineer, "国籍", "select")
    if nationality and str(nationality).strip() and str(nationality).strip() != "日本":
        reasons.append("外国籍")

    residence = extract_prop(engineer, "居住地", "select")
    if residence and str(residence).strip() and not _is_kanto(str(residence).strip()):
        reasons.append(f"地方人材: {residence}")

    end_date = _parse_date(extract_prop(engineer, "稼働終了日", "date"))
    if end_date is not None:
        days_blank = (reference - end_date).days
        if days_blank > BLANK_DAYS_THRESHOLD:
            reasons.append(f"ブランク{days_blank}日")

    if extract_prop(engineer, "短期連続フラグ", "checkbox") is True:
        reasons.append("短期案件連続")

    if extract_prop(engineer, "既往歴フラグ", "checkbox") is True:
        reasons.append("既往歴")

    return (not reasons, reasons)


def format_reasons(reasons: list[str]) -> str:
    return "\n".join(reasons)
