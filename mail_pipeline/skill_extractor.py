"""Rule-first skill extraction for SES project emails."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

ALIASES_PATH = Path(__file__).resolve().parent.parent / "matching_v3" / "skill_aliases.json"

# === ゴミ判定ルール ===
SKILL_BLACKLIST = [
    r"\d+[万円]",
    r"[~〜～]",
    r"[☆★!！*]",
    r"【.*】",
    r"歳まで",
    r"月[〜~]|[〜~]月",
    r"相談可|増員|弊社|注力|募集",
    r"即日|即稼働",
    # 1B: 記号のみ
    r'^[】△▲○◎×>\)\(]+$',
    # 1B: ラベル語
    r'^(スキル|必須|尚可|歓迎|条件|経験)[:：]?$',
    # 1B: 勤務形態
    r'^(フルリモート|リモート|常駐|併用|出社|週\d)$',
    # 1B: 月名・時期
    r'^\d{1,2}月[〜~]?$',
    r'^(即日|即参画|即稼働)$',
    # 1B: 文末表現（文章混入）
    r'(ください|です|ます|となります|ている|ですが|いたします|ございます|お願い)',
    # 1B: ビジネス用語suffix
    r'(案件|要員|募集|面談|単価|人材|配信|展開)$',
    r'制限の管理',
]

# backward compat alias
BLACKLIST_PATTERNS = SKILL_BLACKLIST


def normalize_skill_text(value: str) -> str:
    """全角半角正規化 + 前後の記号除去。"""
    value = unicodedata.normalize('NFKC', value).strip()
    value = re.sub(r'^[\s\-・:：\[\]【】]+|[\s\-・:：\[\]【】]+$', '', value)
    return value


def strip_business_suffix(value: str) -> str:
    """'react案件' -> 'react' などビジネス用語suffixを除去。"""
    return re.sub(r'(案件|要員|募集|人材)$', '', value).strip()


SUFFIX_STRIP_PATTERNS = [
    r'の構築経験$', r'の経験$', r'実務経験$', r'開発経験$', r'構築経験$',
    r'運用経験$', r'設計経験$', r'導入経験$', r'移行経験$',
    r'経験$',
    r'知識$', r'理解$', r'スキル$', r'ができる方$',
    r'の構築$', r'の設計$', r'の開発$', r'の運用$',
    r'での開発$', r'を用いた開発$', r'による開発$',
    r'を使用した$', r'を用いた$', r'による$',
    r'作成$', r'実施$', r'対応$', r'担当$',
]

GENERIC_ONLY_TERMS = {
    'プロファイル', '管理', '経験', '対応', '作業', '構築', '設計',
    '開発', '運用', '保守', 'スキル', '知識', '条件', '業務',
}


def normalize_extracted_skill(value: str) -> str:
    """抽出後スキル正規化: suffix除去・助詞除去・generic-only除去。"""
    result = value.strip()
    for _ in range(6):
        prev = result
        for pat in SUFFIX_STRIP_PATTERNS:
            result = re.sub(pat, '', result).strip()
        result = re.sub(r'(での|による|を用いた|使用した)$', '', result).strip()
        result = re.sub(r'^(の|を|に|で|が)', '', result).strip()
        if result == prev:
            break
    if result in GENERIC_ONLY_TERMS:
        return ''
    return result


@lru_cache(maxsize=1)
def load_skill_aliases() -> dict[str, str]:
    """matching_v3/skill_aliases.json から lower -> canonical の辞書を読み込む。"""
    if not ALIASES_PATH.exists():
        return dict(SKILL_ALIASES)
    data = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
    aliases: dict[str, str] = {}
    for canonical in data.get("canonical_skills", []):
        aliases[str(canonical).lower()] = str(canonical)
    for key, value in data.get("aliases", {}).items():
        aliases[str(key).lower()] = str(value)
    aliases.update({k.lower(): v for k, v in SKILL_ALIASES.items()})
    return aliases


def _load_skill_aliases() -> dict[str, str]:
    """Phase 2 v2: 後方互換エイリアス。"""
    return load_skill_aliases()


def _get_known_skills() -> set[str]:
    aliases = load_skill_aliases()
    return {k.lower() for k in aliases} | {v.lower() for v in aliases.values()}


def _alias_lookup(value: str, aliases: dict[str, str]) -> str | None:
    lower = value.lower()
    if lower in aliases:
        return aliases[lower]
    return None


def _rejection_score(value: str) -> int:
    """文章断片らしさのスコア。3以上で reject（Step 3.5）。辞書ヒット済みはここに到達しない。"""
    score = 0
    if re.match(r'^(および|または|もしくは|ならびに|かつ)', value):
        score += 2
    particles = len(re.findall(r'[のをにでがはもとへ]', value))
    if particles >= 3:
        score += 2
    if len(value) > 15:
        score += 2
    biz_words = re.findall(r'(経験|業務|対応|提案|推進|管理|支援|確認|作成|実施|調整)', value)
    if len(biz_words) >= 2:
        score += 3
    elif len(biz_words) == 1:
        score += 1
    if re.search(r'(レベル|程度|以上|相当|未満|年以上)$', value):
        score += 1
    if particles >= 1 and len(biz_words) >= 1:
        score += 2
    return score


def _load_matching_denylist_flat() -> frozenset[str]:
    denylist_path = Path(__file__).resolve().parent.parent / "matching_v3" / "denylist.json"
    if not denylist_path.exists():
        return frozenset()
    try:
        data = json.loads(denylist_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return frozenset()
    flat: set[str] = set()
    for values in data.values():
        if isinstance(values, list):
            for item in values:
                flat.add(str(item).strip().lower())
    return frozenset(flat)


_MATCHING_DENYLIST_FLAT = _load_matching_denylist_flat()


def validate_skill(value: str, aliases: dict | None = None) -> tuple[bool, str]:
    """スキル値が正当かどうか判定。Returns (is_valid, canonical_value)。"""
    aliases = aliases if aliases is not None else load_skill_aliases()
    value = normalize_skill_text(value)
    if not value or len(value) < 2:
        return False, value

    if value.lower() in _MATCHING_DENYLIST_FLAT:
        return False, value
    if re.search(r"[】【\[\]{}]", value):
        return False, value

    # Step 1: 辞書allowlist
    hit = _alias_lookup(value, aliases)
    if hit:
        return True, hit

    # Step 2: normalize_extracted_skill -> 再辞書チェック
    normalized = normalize_extracted_skill(value)
    if normalized:
        hit = _alias_lookup(normalized, aliases)
        if hit:
            return True, hit

    # business suffix 除去 -> 再チェック
    stripped = strip_business_suffix(value)
    if stripped != value:
        hit = _alias_lookup(stripped, aliases)
        if hit:
            return True, hit
        norm_stripped = normalize_extracted_skill(stripped)
        if norm_stripped:
            hit = _alias_lookup(norm_stripped, aliases)
            if hit:
                return True, hit

    # Step 3: blacklist
    for candidate in (value, normalized, stripped):
        if not candidate:
            continue
        for pat in SKILL_BLACKLIST:
            if re.search(pat, candidate):
                return False, value

    # Step 3.5: スコアベース拒否
    if _rejection_score(value) >= 3:
        return False, value

    # Step 4: ポジティブパターン
    if len(value) > 30:
        return False, value
    if re.fullmatch(r'[A-Za-z]{1,3}', value):
        ok = value.lower() in _get_known_skills()
        return ok, value if ok else value
    if re.fullmatch(r"[\d０-９.]+", value):
        return False, value
    if re.fullmatch(r"[A-Za-z0-9#.+/\- ]{2,30}", value):
        return True, value
    if re.fullmatch(r"[゠-ヿー]{2,15}", value):
        return True, value
    if re.fullmatch(r"[一-鿿゠-ヿ]{2,12}", value):
        return True, value
    if re.fullmatch(r".{2,15}(経験|設計|構築|開発|運用|保守|管理|テスト|移行)", value):
        return True, value
    if len(value) <= 20 and re.search(r"[A-Za-z]", value) and re.search(r"[\u3000-\u9FFF]", value):
        return True, value

    return False, value


def filter_skills(
    raw_skills: list, aliases: dict | None = None
) -> tuple[list[str], list[str], list[str]]:
    """バリデーションして (valid, rejected, cleaned) を返す。validはcanonical form。"""
    aliases = aliases if aliases is not None else load_skill_aliases()
    valid: list[str] = []
    rejected: list[str] = []
    cleaned: list[str] = []
    for s in raw_skills:
        if not s or not str(s).strip():
            rejected.append(s)
            continue
        raw_norm = normalize_skill_text(str(s))
        is_valid, canon = validate_skill(str(s), aliases)
        if is_valid and canon:
            if canon.lower() != raw_norm.lower() and canon != str(s).strip():
                cleaned.append(canon)
            valid.append(canon)
        else:
            rejected.append(s)
    # 重複除去・順序保持
    valid = list(dict.fromkeys(valid))
    cleaned = list(dict.fromkeys(cleaned))
    return valid, rejected, cleaned


KNOWN_SKILLS = {
    "java",
    "python",
    "go",
    "php",
    "ruby",
    "c#",
    "kotlin",
    "scala",
    "javascript",
    "typescript",
    "swift",
    "objective-c",
    "dart",
    "rust",
    "vb.net",
    "vba",
    "cobol",
    "pl/sql",
    "pl/i",
    "c++",
    "c言語",
    "perl",
    "spring",
    "spring boot",
    "django",
    "laravel",
    "rails",
    "flask",
    "react",
    "vue",
    "angular",
    "next.js",
    "nuxt",
    "node.js",
    "express",
    "flutter",
    "mybatis",
    "struts",
    "hibernate",
    "oracle",
    "mysql",
    "postgresql",
    "sql server",
    "redis",
    "dynamodb",
    "mongodb",
    "aurora",
    "sql",
    "aws",
    "azure",
    "gcp",
    "google cloud",
    "docker",
    "kubernetes",
    "terraform",
    "ansible",
    "linux",
    "windows server",
    "vmware",
    "cisco",
    "jp1",
    "zabbix",
    "nagios",
    "git",
    "jenkins",
    "jira",
    "confluence",
    "pmo",
    "pm",
    "pl",
    "se",
    "sre",
    "dba",
    "sap",
    "salesforce",
    "servicenow",
    "dynamics",
    "grandit",
    "uipath",
    "power bi",
    "tableau",
    "excel",
    "rpa",
    "fortigate",
    "splunk",
    "etl",
    "unity",
    "dataspider",
    "asteria",
    "prisma",
    "sase",
    "hulft",
    "ai",
    "ml",
    "qa",
    "ios",
}

HEADER_PATTERNS: list[tuple[str, str]] = [
    (r"(?:必要|必須)(?:スキル)?[：:]\s*(.*?)(?:\n|$)", "required"),
    (r"■必須[：:\s]*(.*?)(?:\n|$)", "required"),
    (r"【必要スキル】(.*?)(?:\n|$)", "required"),
    (r"【必須】(.*?)(?:\n|$)", "required"),
    (r"(?:尚可|歓迎)(?:スキル)?[：:]\s*(.*?)(?:\n|$)", "optional"),
    (r"【尚可】(.*?)(?:\n|$)", "optional"),
]

# Phase 3: section-aware 必須/尚可 抽出用パターン
REQUIRED_HEADERS = [
    r'【必須】', r'■必須', r'必須スキル', r'必須条件', r'MUST',
    r'必要な経験', r'必須要件', r'求めるスキル',
]
OPTIONAL_HEADERS = [
    r'【尚可】', r'■尚可', r'■歓迎', r'尚可スキル', r'歓迎スキル',
    r'あると尚可', r'歓迎条件', r'あれば尚良', r'WANT', r'Nice to have',
]
SECTION_BREAK = [
    r'^【', r'^■', r'^━', r'^-{3,}', r'^\*{3,}',
    r'単価', r'勤務地', r'期間', r'面談', r'備考',
]

_REQUIRED_HEADER_RE = re.compile(r'|'.join(REQUIRED_HEADERS), re.IGNORECASE)
_OPTIONAL_HEADER_RE = re.compile(r'|'.join(OPTIONAL_HEADERS), re.IGNORECASE)
_SECTION_BREAK_RE = re.compile(r'|'.join(SECTION_BREAK))


def _section_aware_extract(text: str) -> dict:
    """行単位でセクションヘッダーを検出し必須/尚可スキルを分離。

    Returns: {"required": set, "optional": set, "hit": bool}
    hit=False の場合はヘッダーが見つからなかった（フォールバック必要）。
    """
    required: set[str] = set()
    optional: set[str] = set()
    current_section: str | None = None
    header_hit = False

    for line in text.splitlines():
        line_s = line.strip()
        if not line_s:
            continue

        if _REQUIRED_HEADER_RE.search(line_s):
            current_section = "required"
            header_hit = True
            rest = _REQUIRED_HEADER_RE.sub('', line_s, count=1).strip()
            rest = re.sub(r'^[\s:：]+', '', rest)
            if rest:
                required.update(_split_skills(rest))
            continue

        if _OPTIONAL_HEADER_RE.search(line_s):
            current_section = "optional"
            header_hit = True
            rest = _OPTIONAL_HEADER_RE.sub('', line_s, count=1).strip()
            rest = re.sub(r'^[\s:：]+', '', rest)
            if rest:
                optional.update(_split_skills(rest))
            continue

        if _SECTION_BREAK_RE.search(line_s):
            current_section = None
            continue

        if current_section == "required":
            required.update(_split_skills(line_s))
        elif current_section == "optional":
            optional.update(_split_skills(line_s))

    return {"required": required, "optional": optional, "hit": header_hit}

SKILL_ALIASES: dict[str, str] = {
    "java": "Java",
    "python": "Python",
    "php": "PHP",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "c#": "C#",
    "node.js": "Node.js",
    "react": "React",
    "aws": "AWS",
    "go": "Go",
    "ruby": "Ruby",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "vue": "Vue.js",
    "angular": "Angular",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "gcp": "GCP",
    "azure": "Azure",
    "spring": "Spring",
    "spring boot": "Spring",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "oracle": "Oracle",
    "mongodb": "MongoDB",
    "linux": "Linux",
    "html/css": "JavaScript",
    "fortigate": "インフラ",
    "cisco": "インフラ",
    "hulft": "インフラ",
    "jp1": "インフラ",
    "splunk": "インフラ",
    "servicenow": "インフラ",
    "etl": "インフラ",
    "terraform": "インフラ",
    "unity": "C#",
    "dataspider": "インフラ",
    "asteria": "インフラ",
    "sap": "インフラ",
    "prisma": "インフラ",
    "sase": "インフラ",
}


_INLINE_NICE_RAW = [
    r"尚可[：:]\s*(.+?)(?:\n|$)",
    r"歓迎[：:]\s*(.+?)(?:\n|$)",
    r"あれば尚良[しい]?[：:]\s*(.+?)(?:\n|$)",
    r"プラス要件[：:]\s*(.+?)(?:\n|$)",
    r"尚可[）\)]\s*(.+?)(?:\n|$)",
    r"Nice\s*to\s*have[：:]\s*(.+?)(?:\n|$)",
    r"WANT[：:]\s*(.+?)(?:\n|$)",
    r"優遇[：:]\s*(.+?)(?:\n|$)",
    r"歓迎スキル[：:]\s*(.+?)(?:\n|$)",
    r"必須[：:].*?[/／]\s*尚可[：:]\s*(.+?)(?:\n|$)",
]
INLINE_NICE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _INLINE_NICE_RAW]
_OPTIONAL_HINT_WORDS = ("尚可", "歓迎", "あれば尚良", "nice to have", "want", "優遇", "プラス要件")


def _extract_inline_optional(text: str) -> set[str]:
    """1行内の尚可/歓迎パターンからスキルを抽出。"""
    found: set[str] = set()
    for pattern in INLINE_NICE_PATTERNS:
        for match in pattern.finditer(text):
            chunk = match.group(1).strip()
            if chunk:
                found.update(_split_skills(chunk))
    return found


def _llm_extract_optional(body: str) -> list[str]:
    """尚可スキルのLLM fallback（CostGuard未設定時は空を返す）。"""
    import os

    if os.environ.get("SKILL_OPTIONAL_LLM_ENABLED", "0") != "1":
        return []
    try:
        from cost_guard import allowed, finalize
        import requests as _requests

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return []
        decision = allowed(
            phase="classify",
            block_type="skill_optional",
            target_id="optional-skill-extract",
            est_in=len(body) // 4 + 200,
            est_out=200,
            model_hint="claude-haiku-4-5-20251001",
            script="skill_extractor",
        )
        if not decision.allowed:
            return []
        prompt = (
            "以下のメール文面から「あると望ましいスキル（尚可・歓迎スキル）」のみを抽出してください。\n"
            "必須スキルは含めないでください。\n"
            "原子的なスキル名のみ返してください（文章は不可）。\n"
            'JSON配列で返してください: ["skill1", "skill2"]\n'
            "該当なしの場合は空配列 [] を返してください。\n\n"
            f"{body[:2000]}"
        )
        res = _requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        if res.status_code != 200:
            finalize(decision, success=False, error_kind="transient")
            return []
        content = res.json().get("content", [])
        text = content[0].get("text", "[]") if content else "[]"
        parsed = json.loads(re.sub(r"```json|```", "", text).strip() or "[]")
        finalize(decision, success=True)
        return [str(s) for s in parsed if isinstance(s, str)]
    except Exception as exc:
        logger.warning("optional LLM fallback failed: %s", exc)
        return []


def extract_skills(subject: str, body: str) -> dict:
    """Extract required/optional skills from subject and body."""
    required: set[str] = set()
    optional: set[str] = set()

    subject_norm = unicodedata.normalize("NFKC", subject or "")
    body_norm = unicodedata.normalize("NFKC", (body or "")[:2000])
    header_hit = False

    # Phase 3: section-aware extraction (body only)
    section_result = _section_aware_extract(body_norm)
    if section_result["hit"]:
        header_hit = True
        required.update(section_result["required"])
        optional.update(section_result["optional"])
    else:
        # inline尚可パターン
        inline_optional = _extract_inline_optional(body_norm)
        if inline_optional:
            optional.update(inline_optional)
            header_hit = True
        # Fallback: legacy HEADER_PATTERNS on subject+body
        text_full = f"{subject_norm} {body_norm}"
        for pattern, kind in HEADER_PATTERNS:
            for match in re.finditer(pattern, text_full, re.IGNORECASE):
                found = _split_skills(match.group(1))
                if not found:
                    continue
                header_hit = True
                if kind == "required":
                    required.update(found)
                else:
                    optional.update(found)

    if not optional and any(h in body_norm for h in _OPTIONAL_HINT_WORDS):
        for skill in _llm_extract_optional(body_norm):
            optional.add(skill.lower())

    # Subject bracket lists: 【React, TypeScript, AWS】 or [Java/Spring]
    for match in re.finditer(r"[【\[]([^\]】]+)[\]】]", subject_norm):
        chunk = match.group(1)
        if _looks_like_skill_list(chunk):
            required.update(_split_skills(chunk.replace("/", ",")))

    # Slash/comma skill tokens in subject (e.g. PM,PMO Java/GO)
    if subject_norm:
        for token in re.split(r"[/|｜]", subject_norm):
            token = token.strip()
            if token and _is_known_skill_token(token):
                required.add(token.lower())

    text_lower = f"{subject_norm} {body_norm}".lower()
    if not header_hit:
        for skill in sorted(KNOWN_SKILLS, key=len, reverse=True):
            if skill in text_lower:
                required.add(skill)

    source = "header" if header_hit else ("dictionary" if required or optional else "none")
    valid_required, rejected_required, _ = filter_skills(list(required))
    valid_optional, rejected_optional, _ = filter_skills(list(optional))
    if rejected_required or rejected_optional:
        logger.info(
            "skill_extractor: rejected %d required, %d optional as garbage: %s %s",
            len(rejected_required),
            len(rejected_optional),
            rejected_required[:5],
            rejected_optional[:5],
        )
    return {
        "required": sorted(valid_required),
        "optional": sorted(valid_optional),
        "source": source,
    }


def _looks_like_skill_list(chunk: str) -> bool:
    lower = chunk.lower()
    if any(skill in lower for skill in KNOWN_SKILLS):
        return True
    if re.search(r"(?:react|java|python|aws|vue|typescript|kotlin|sql|pmo|pm\b)", lower):
        return True
    return "," in chunk or "、" in chunk


def _is_known_skill_token(token: str) -> bool:
    cleaned = re.sub(r"[\d万円~〜\-]+", "", token).strip().lower()
    if not cleaned or len(cleaned) > 40:
        return False
    if cleaned in KNOWN_SKILLS:
        return True
    return any(skill in cleaned for skill in ("java", "react", "vue", "python", "aws", "pmo", "go", "sql"))


def normalize_to_valid_skills(skills: list[str], valid_skills: list[str]) -> list[str]:
    """Map extracted skill names to Notion VALID_SKILLS entries."""
    valid_lower = {s.lower(): s for s in valid_skills}
    out: list[str] = []
    seen: set[str] = set()
    for raw in skills:
        key = raw.strip().lower()
        if not key:
            continue
        mapped = valid_lower.get(key) or SKILL_ALIASES.get(key)
        if not mapped:
            for valid in valid_skills:
                if valid.lower() in key or key in valid.lower():
                    mapped = valid
                    break
        if mapped and mapped not in seen:
            seen.add(mapped)
            out.append(mapped)
    return out


def merge_extracted_skills(
    ai_required: list[str],
    ai_optional: list[str],
    subject: str,
    body: str,
    valid_skills: list[str],
) -> tuple[list[str], list[str]]:
    """Merge AI and rule-based skills, normalized to VALID_SKILLS."""
    rule_result = extract_skills(subject, body)
    merged_required = list({*(s.lower() for s in ai_required), *rule_result["required"]})
    merged_optional = list({*(s.lower() for s in ai_optional), *rule_result["optional"]})
    req = normalize_to_valid_skills(merged_required, valid_skills)
    opt = normalize_to_valid_skills(merged_optional, valid_skills)
    opt = [s for s in opt if s not in req]
    return req, opt


def _split_skills(text: str) -> set[str]:
    parts = re.split(r"[,、/|・\n　]", text)
    result: set[str] = set()
    for part in parts:
        part = part.strip()
        if not part:
            continue
        part = re.sub(r"[(（][^)）]*[)）]", "", part).strip()
        part = re.sub(r"\d+年以上", "", part).strip()
        if part:
            result.add(part.lower())
    return result
