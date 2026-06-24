from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

KANTO_PREFECTURES = ["東京", "神奈川", "埼玉", "千葉", "茨城", "栃木", "群馬"]

FOREIGN_KEYWORDS = [
    "外国籍",
    "中国語",
    "韓国語",
    "ベトナム",
    "フィリピン",
    "インド",
    "ネパール",
    "中国人",
    "韓国人",
    "中国",
    "韓国",
]

STATION_TO_PREFECTURE: dict[str, str] = {
    "渋谷": "東京",
    "新宿": "東京",
    "池袋": "東京",
    "品川": "東京",
    "秋葉原": "東京",
    "東京": "東京",
    "上野": "東京",
    "銀座": "東京",
    "六本木": "東京",
    "恵比寿": "東京",
    "目黒": "東京",
    "五反田": "東京",
    "大崎": "東京",
    "赤羽": "東京",
    "北千住": "東京",
    "錦糸町": "東京",
    "吉祥寺": "東京",
    "三鷹": "東京",
    "立川": "東京",
    "八王子": "東京",
    "横浜": "神奈川",
    "川崎": "神奈川",
    "武蔵小杉": "神奈川",
    "藤沢": "神奈川",
    "大宮": "埼玉",
    "浦和": "埼玉",
    "川口": "埼玉",
    "所沢": "埼玉",
    "柏": "千葉",
    "市川": "千葉",
    "船橋": "千葉",
    "千葉": "千葉",
    "幕張": "千葉",
    "大阪": "大阪",
    "梅田": "大阪",
    "名古屋": "愛知",
    "京都": "京都",
    "福岡": "福岡",
    "札幌": "北海道",
    "仙台": "宮城",
}

WEAK_NAME_PATTERNS = ("不明", "未記", "未設定", "名前未設定", "氏名不明")
INITIAL_PATTERN = re.compile(r"^[A-Za-z]\.?$")
INITIALS_PATTERN = re.compile(r"^[A-Za-z][\.・][A-Za-z]\.?$")
SHORT_LATIN_PATTERN = re.compile(r"^[A-Za-z]{2,3}$")
HIRAGANA_PATTERN = re.compile(r"[\u3040-\u309F]")
KATAKANA_PATTERN = re.compile(r"[\u30A0-\u30FF]")
KANJI_PATTERN = re.compile(r"[\u4E00-\u9FFF]")
LATIN_PATTERN = re.compile(r"[A-Za-z]")
ID_ALPHA_DIGITS_PATTERN = re.compile(r"^[A-Za-z]{2,3}\d{4,}$", re.IGNORECASE)
ID_PREFIX_PATTERN = re.compile(r"^(?:No\.|N0|ID:)", re.IGNORECASE)
ID_ALNUM_CODE_PATTERN = re.compile(r"^[A-Za-z0-9]+$")
SHORT_ALPHA_PART_PATTERN = re.compile(r"^[A-Za-z]{2,3}$")

SES_WORK = Path(__file__).resolve().parent.parent
if str(SES_WORK) not in sys.path:
    sys.path.insert(0, str(SES_WORK))

ENV_PATH = SES_WORK / "config" / ".env"
NATIONALITY_LLM_MODEL = "gpt-4.1-nano"
SCRIPT_NAME = "flag_auto_updater"
LLM_MAX_TOKENS = 10

NATIONALITY_LLM_SYSTEM_PROMPT = """あなたはSES業界の人材データ整理AIです。
エンジニアの氏名と備考から国籍を判定してください。
回答は必ず以下のいずれか1単語のみ返してください:
日本 / 外国籍候補 / 要確認

判定基準:
- 備考に外国語・外国籍を示す情報がある → 外国籍候補
- 備考に居住地・路線・スキル等の日本語情報がある → 日本
- イニシャル・IDコード形式で備考にも手がかりなし → 要確認
- 判断材料が全くない → 要確認"""


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return unicodedata.normalize("NFKC", str(value)).strip()


def _core_name(name: str) -> str:
    normalized = _normalize_text(name)
    for sep in ("（", "(", "／", "/"):
        if sep in normalized:
            normalized = normalized.split(sep, 1)[0].strip()
    return normalized


def _find_foreign_keyword(text: str) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None
    for keyword in FOREIGN_KEYWORDS:
        if keyword in normalized:
            return keyword
    return None


def _has_japanese(text: str) -> bool:
    return bool(HIRAGANA_PATTERN.search(text) or KATAKANA_PATTERN.search(text) or KANJI_PATTERN.search(text))


def _is_strong_id_code_part(part: str) -> bool:
    if ID_ALPHA_DIGITS_PATTERN.fullmatch(part):
        return True
    if ID_PREFIX_PATTERN.match(part):
        return True
    if (
        ID_ALNUM_CODE_PATTERN.fullmatch(part)
        and any(char.isdigit() for char in part)
        and len(part) >= 4
        and not _has_japanese(part)
    ):
        return True
    return False


def _is_id_code_part(part: str) -> bool:
    part = _normalize_text(part)
    if not part or _has_japanese(part):
        return False
    if _is_strong_id_code_part(part):
        return True
    return bool(SHORT_ALPHA_PART_PATTERN.fullmatch(part))


def is_id_code(name: str) -> bool:
    normalized = _normalize_text(name)
    if not normalized or _has_japanese(normalized):
        return False

    parts = normalized.split()
    if len(parts) == 1:
        return _is_strong_id_code_part(parts[0])

    if not all(_is_id_code_part(part) for part in parts):
        return False
    return any(_is_strong_id_code_part(part) for part in parts)


def is_alphabetic_dominant_name(name: str) -> bool:
    normalized = _core_name(name)
    if not normalized:
        return False
    if INITIALS_PATTERN.fullmatch(normalized) or SHORT_LATIN_PATTERN.fullmatch(normalized):
        return False
    letters = LATIN_PATTERN.findall(normalized)
    if not letters:
        return False
    japanese_chars = (
        len(HIRAGANA_PATTERN.findall(normalized))
        + len(KATAKANA_PATTERN.findall(normalized))
        + len(KANJI_PATTERN.findall(normalized))
    )
    if " " in normalized and len(letters) >= 4:
        return True
    return len(letters) >= 5 and len(letters) > japanese_chars


def is_clearly_japanese_name(name: str) -> bool:
    normalized = _core_name(name)
    if not normalized:
        return False
    if is_alphabetic_dominant_name(normalized):
        return False
    return bool(
        KANJI_PATTERN.search(normalized) or KATAKANA_PATTERN.search(normalized) or HIRAGANA_PATTERN.search(normalized)
    )


def is_weak_name(name: str) -> bool:
    normalized = _core_name(name)
    if not normalized:
        return True
    if normalized in WEAK_NAME_PATTERNS:
        return True
    if INITIAL_PATTERN.fullmatch(normalized):
        return True
    return False


def estimate_nationality(name: str, memo: str = "") -> tuple[str, str]:
    """国籍を推定し (値, 根拠) を返す。"""
    normalized_name = _core_name(name)
    normalized_memo = _normalize_text(memo)

    keyword = _find_foreign_keyword(normalized_memo)
    if keyword:
        return "外国籍候補", f"備考に「{keyword}」"

    if is_alphabetic_dominant_name(normalized_name):
        return "外国籍候補", f"氏名がアルファベット主体: {normalized_name}"

    if is_id_code(name):
        return "要確認", "IDコード形式のため判定スキップ"

    if is_weak_name(normalized_name):
        return "要確認", "氏名から国籍を判定できない"

    if is_clearly_japanese_name(normalized_name):
        return "日本", f"氏名が日本語表記: {normalized_name}"

    if INITIALS_PATTERN.fullmatch(normalized_name) or SHORT_LATIN_PATTERN.fullmatch(normalized_name):
        return "日本", f"イニシャル表記（外国籍キーワードなし）: {normalized_name}"

    return "要確認", "判定根拠が弱い"


def _normalize_llm_nationality(text: str) -> str:
    normalized = _normalize_text(text)
    for value in ("外国籍候補", "要確認", "日本"):
        if value in normalized:
            return value
    return "要確認"


def _load_openai_api_key() -> str | None:
    from dotenv import dotenv_values

    env = dotenv_values(ENV_PATH, encoding="utf-8")
    return env.get("OPENAI_API_KEY")


def _call_openai_nationality(name: str, memo: str) -> tuple[str, str]:
    from openai import OpenAI

    from common.ledger import can_spend, record

    user_prompt = f"氏名: {name}\n備考: {memo}"
    est_input_tokens = len(user_prompt) // 4 + len(NATIONALITY_LLM_SYSTEM_PROMPT) // 4 + 50
    est_output_tokens = LLM_MAX_TOKENS

    if not can_spend(est_input_tokens, est_output_tokens, NATIONALITY_LLM_MODEL):
        return "要確認", "LLMエラー"

    api_key = _load_openai_api_key()
    if not api_key:
        return "要確認", "LLMエラー"

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=NATIONALITY_LLM_MODEL,
        max_tokens=LLM_MAX_TOKENS,
        temperature=0,
        messages=[
            {"role": "system", "content": NATIONALITY_LLM_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    usage = response.usage
    input_tokens = int(getattr(usage, "prompt_tokens", None) or est_input_tokens)
    output_tokens = int(getattr(usage, "completion_tokens", None) or est_output_tokens)
    record(input_tokens, output_tokens, NATIONALITY_LLM_MODEL, SCRIPT_NAME)

    content = response.choices[0].message.content or ""
    value = _normalize_llm_nationality(content)
    return value, f"LLM判定: {content.strip()}"


def estimate_nationality_llm(name: str, memo: str = "") -> tuple[str, str]:
    normalized_memo = _normalize_text(memo)

    if is_id_code(name):
        return "要確認", "判定材料なし"

    if is_weak_name(name) and not normalized_memo:
        return "要確認", "判定材料なし"

    try:
        return _call_openai_nationality(name, normalized_memo)
    except Exception:
        return "要確認", "LLMエラー"


def extract_residence_from_memo(memo: str) -> tuple[str | None, str | None]:
    """備考から居住地（都道府県）を推定し (値, 根拠) を返す。"""
    normalized = _normalize_text(memo)
    if not normalized:
        return None, None

    matches: list[tuple[int, str, str]] = []
    for station, prefecture in STATION_TO_PREFECTURE.items():
        index = normalized.find(station)
        if index >= 0:
            matches.append((index, station, prefecture))

    if not matches:
        return None, None

    matches.sort(key=lambda item: (-len(item[1]), item[0]))
    _, station, prefecture = matches[0]
    return prefecture, f"備考の駅名「{station}」"


def build_notion_page_url(page_id: str) -> str:
    page_key = page_id.replace("-", "")
    return f"https://www.notion.so/{page_key}"
