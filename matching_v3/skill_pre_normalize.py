"""スキル表記の共通正規化（skill_aliases.json 参照前段）。"""

from __future__ import annotations

import re
import unicodedata
from typing import Callable

# カタカナ表記 → 英語 canonical 名（完全一致置換）
_KATAKANA_TO_LATIN: dict[str, str] = {
    "ジャバ": "Java",
    "ジャバスクリプト": "JavaScript",
    "パイソン": "Python",
    "タイプスクリプト": "TypeScript",
    "ゴー": "Go",
    "ルビー": "Ruby",
    "ノード": "Node.js",
    "ノードjs": "Node.js",
    "ノード.js": "Node.js",
    "リエクト": "React",
    "リアクト": "React",
    "ビーエムエル": "BML",
    "エーダブリューエス": "AWS",
    "アジュール": "Azure",
    "ジーシーピー": "GCP",
    "ドッカー": "Docker",
    "クバネティス": "Kubernetes",
    "クバネテス": "Kubernetes",
    "ポストグレス": "PostgreSQL",
    "ポストグレスql": "PostgreSQL",
    "マイエスキューエル": "MySQL",
    "オラクル": "Oracle",
    "スプリング": "Spring",
    "スプリングブート": "Spring Boot",
    "ビーディーネット": "VB.NET",
    "ブイビーネット": "VB.NET",
    "シーシャープ": "C#",
    "シープラスプラス": "C++",
    "エックスエムエル": "XML",
    "エイチティーエムエル": "HTML",
    "シーエスエス": "CSS",
    "テラフォーム": "Terraform",
    "アンシブル": "Ansible",
    "ジェンキンス": "Jenkins",
    "ギット": "Git",
    "ギットハブ": "GitHub",
    "ギットラブ": "GitLab",
    "リナックス": "Linux",
    "ウィンドウズ": "Windows",
    "セールスフォース": "Salesforce",
    "セキュリティ": "セキュリティ",
}

# 記号・表記ゆれ（部分一致）
_SYMBOL_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"c\s*＃|c\s*#|c\s*sharp|c-sharp", re.IGNORECASE), "C#"),
    (re.compile(r"c\s*\+\s*\+", re.IGNORECASE), "C++"),
    (re.compile(r"node\s*\.?\s*js|nodejs", re.IGNORECASE), "Node.js"),
    (re.compile(r"react\s*\.?\s*js|reactjs", re.IGNORECASE), "React"),
    (re.compile(r"vue\s*\.?\s*js|vuejs", re.IGNORECASE), "Vue.js"),
    (re.compile(r"angular\s*js|angularjs", re.IGNORECASE), "Angular"),
    (re.compile(r"asp\s*\.?\s*net", re.IGNORECASE), "ASP.NET"),
    (re.compile(r"vb\s*[\.\・\s]+\s*net", re.IGNORECASE), "VB.NET"),
    (re.compile(r"\.net\s*core|dotnet\s*core", re.IGNORECASE), ".NET Core"),
    (re.compile(r"spring\s*boot", re.IGNORECASE), "Spring Boot"),
    (re.compile(r"spring\s*framework", re.IGNORECASE), "Spring"),
    (re.compile(r"amazon\s*web\s*services", re.IGNORECASE), "AWS"),
    (re.compile(r"google\s*cloud\s*platform", re.IGNORECASE), "GCP"),
    (re.compile(r"microsoft\s*azure", re.IGNORECASE), "Azure"),
]

# 技術名 + 運用系サフィックス → ベース技術名（P1補助）
_TECH_OPS_SUFFIX_RE = re.compile(
    r"^(.+?)(?:運用保守|運用・保守|運用/保守|運用管理|構築運用|導入運用|保守運用)$"
)

# lookup-time 経験 末尾strip（alias登録はしない）
_EXP_SUFFIX_STRIP_RE = re.compile(r"(?:の?ご?経験者?|実務経験|業務経験)$")


def pre_normalize_skill_text(raw_skill: str) -> str:
    """NFKC・表記ゆれを skill_aliases 参照前に統一する。"""
    text = unicodedata.normalize("NFKC", (raw_skill or "").strip())
    if not text:
        return text

    # 前後の装飾記号
    text = re.sub(r"^[\s\-・:：\[\]【】()（）]+|[\s\-・:：\[\]【】()（）]+$", "", text)

    # カタカナ → 英語（長い語から）
    lowered = text.lower()
    for kana, latin in sorted(_KATAKANA_TO_LATIN.items(), key=lambda x: len(x[0]), reverse=True):
        if kana.lower() in lowered:
            text = re.sub(re.escape(kana), latin, text, flags=re.IGNORECASE)

    # 記号ゆれ
    for pattern, replacement in _SYMBOL_REPLACEMENTS:
        text = pattern.sub(replacement, text)

    # 技術名+運用保守 等
    m = _TECH_OPS_SUFFIX_RE.match(text)
    if m:
        text = m.group(1).strip()

    # 連続スペース・中黒の正規化（VB . NET 等）
    text = re.sub(r"[\s・]+", " ", text).strip()
    text = re.sub(r"\s*\.\s*", ".", text)

    return text


def skill_lookup_key(skill: str) -> str:
    """エイリアス辞書ルックアップ用キー（小文字 + 空白正規化）。"""
    return " ".join(pre_normalize_skill_text(skill).lower().split())


def pre_normalize_skill_tokens(
    raw: str,
    lookup: "Callable[[str], str | None] | None" = None,
) -> "list[str]":
    """スキル文字列を 1〜2 トークンに分解する。

    - 「技術名 + 運用保守」系: [ベース技術名, "運用保守"] の 2 トークンを返す
    - 「XX 経験/経験者」末尾: lookup で辞書ヒットする場合のみ strip 後の 1 トークン
    - その他: [pre_normalize_skill_text(raw)] の 1 トークン
    既存 pre_normalize_skill_text は後方互換維持（str 返却のまま）。
    """
    text = unicodedata.normalize("NFKC", (raw or "").strip())
    if not text:
        return []

    text = re.sub(r"^[\s\-・:：\[\]【】()（）]+|[\s\-・:：\[\]【】()（）]+$", "", text)

    lowered = text.lower()
    for kana, latin in sorted(_KATAKANA_TO_LATIN.items(), key=lambda x: len(x[0]), reverse=True):
        if kana.lower() in lowered:
            text = re.sub(re.escape(kana), latin, text, flags=re.IGNORECASE)

    for pattern, replacement in _SYMBOL_REPLACEMENTS:
        text = pattern.sub(replacement, text)

    text = re.sub(r"[\s・]+", " ", text).strip()
    text = re.sub(r"\s*\.\s*", ".", text)

    # 技術名 + 運用保守 → 2 トークン化
    m = _TECH_OPS_SUFFIX_RE.match(text)
    if m:
        base = m.group(1).strip()
        return [base, "運用保守"]

    # 経験/経験者 末尾 strip（lookup-time 限定）
    if lookup is not None:
        m2 = _EXP_SUFFIX_STRIP_RE.search(text)
        if m2:
            stripped = text[: m2.start()].strip()
            if stripped and lookup(stripped) is not None:
                return [stripped]

    return [text]
