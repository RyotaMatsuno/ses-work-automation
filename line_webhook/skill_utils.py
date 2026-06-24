"""
skill_utils.py - スキル正規化・マッチングユーティリティ
webhook_server.py / matching_logic.py から共通利用する
"""

import re
import unicodedata

SKILL_ALIASES = {
    "aws": {"amazon web services", "aws"},
    "react": {"react.js", "reactjs", "react"},
    "vue": {"vue.js", "vuejs", "vue"},
    "c#": {"csharp", "c#"},
    "javascript": {"js", "javascript"},
    "typescript": {"ts", "typescript"},
    "spring boot": {"springboot", "spring boot", "spring-boot"},
    "spring": {"spring framework", "spring"},
    "next.js": {"nextjs", "next.js", "next"},
    "node.js": {"nodejs", "node.js", "node"},
    ".net": {"dotnet", ".net", "dot net"},
    "python": {"python3", "python"},
    "gcp": {"google cloud platform", "google cloud", "gcp"},
    "azure": {"microsoft azure", "azure"},
    "pmo": {"プロジェクトマネジメント", "pmo"},
    "php": {"php"},
    "mysql": {"mysql"},
    "laravel": {"laravel"},
}


def normalize_skill(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s).lower().strip()
    s = s.replace("　", " ")  # 全角スペース
    s = re.sub(r"\s+", " ", s)
    return s


def skill_match(required_skill, engineer_skills_normalized):
    """
    必須スキル1件がエンジニアスキルセット（正規化済み）にマッチするか判定。
    1. 完全一致
    2. エイリアス一致
    3. 部分一致（3文字以上）
    """
    req = normalize_skill(required_skill)
    if not req:
        return False
    if req in engineer_skills_normalized:
        return True
    for canonical, aliases in SKILL_ALIASES.items():
        if req == canonical or req in aliases:
            for alias in aliases | {canonical}:
                if alias in engineer_skills_normalized:
                    return True
    # Token-based exact match (no substring: "java" must not match "javascript")
    # Only match if req appears as a whole token separated by /,. or boundaries
    if len(req) >= 2:
        import re
        req_pattern = re.compile(r"(?:^|[/,.\s・|])(" + re.escape(req) + r")(?:$|[/,.\s・|])")
        for eng_s in engineer_skills_normalized:
            if req_pattern.search(eng_s) or eng_s == req:
                return True
    return False


def build_normalized_skill_set(skills):
    """スキルリストを正規化済みセットに変換"""
    return {normalize_skill(s) for s in skills if s}


def normalize_skill_set(skills):
    """build_normalized_skill_set の別名（line_query側との共通インターフェース）"""
    return build_normalized_skill_set(skills)


def has_skill_skip(note):
    """備考に #skill_skip タグがあるか判定"""
    return "#skill_skip" in (note or "")
