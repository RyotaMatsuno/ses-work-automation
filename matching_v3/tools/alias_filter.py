"""alias_filter.py — 923件OOV拡張分から高品質エントリのみ選別する。

入力: skill_aliases_expanded_20260703.json と skill_aliases.json の差分923件
出力: tools/output/ 以下
  - alias_candidates_filtered.json （通過分）
  - alias_rejected_report.csv       （REJECT理由コード付き）
  - review_queue.csv                （R16 review行き）
  - new_canonical_candidates.csv    （R5振替分）
  - skip_exp_report.csv             （SKIP_EXP）
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

BASE_ALIASES_PATH = BASE_DIR / "skill_aliases.json"
EXPANDED_ALIASES_PATH = BASE_DIR / "skill_aliases_expanded_20260703.json"
DENYLIST_PATH = BASE_DIR / "denylist.json"

# ── ルール定数 ────────────────────────────────────────────────

_JOSHI_RE = re.compile(r"[のをがにてへとやもは]")
_JP_MAX = 12
_EN_MAX = 25
_SPACE_REJECT_THRESHOLD = 2  # この数以上の空白で REJECT

_NOISE_CHARS_RE = re.compile(r"[万円【】〜～、。]")
_PAREN_COMMA_RE = re.compile(r"[\(（\)）,、]")

_R3_ALLOWLIST = frozenset(
    [
        "vue3", "vue 3", "java17", "java 17", "java11", "java 11", "java21", "java 21",
        "react18", "react 18", ".net 8", ".net8", "rhel8", "rhel 8", "html5", "css3",
        "python3", "python 3", "node18", "node 18", "node20", "node 20",
        "angular17", "angular 17", "mysql8", "mysql 8",
    ]
)

_DANGER_CANONICALS = frozenset(
    [
        "AI", "AWS", "Java", "設計", "開発", "経験", "テスト", "構築", "運用",
        "開発経験", "運用経験", "運用保守", "進捗管理", "構築経験", "DB",
        # R17: コンピテンシー・汎用職務
        "コミュニケーション力", "主体性", "リーダー", "調整", "実施", "実行", "メール",
        "営業", "ディレクション", "上流工程", "ログ", "SE", "PL", "PM",
    ]
)

_EXP_SUFFIX_RE = re.compile(r"(経験者?|の経験|のご経験|実務経験|業務経験)$")
_CLOUD_PREFIXES = ("aws ", "azure ", "gcp ", "google ", "microsoft ", "ms ")
_R6_EXTRA = frozenset(
    ["sre", "pmo", "dba", "qa", "se", "pm", "pl", "rpa", "cto", "cfo", "coo", "ceo"]
)
_R9_ALLOWLIST = frozenset(["php", "css", "sql", "c#", "c++", "vba", "etl", "vue3", "css3"])
_RECRUIMENT_WORDS_RE = re.compile(r"(案件|募集|対応|担当|可能|歓迎|必須|即日|年以上|年未満|\d+年|要員|豊富|な方|できる方)")
_CONJUNCTION_START_RE = re.compile(r"^(および|または|もしくは|かつ|ならびに)")

# ── ヘルパー ──────────────────────────────────────────────────


def _is_jp_char(ch: str) -> bool:
    o = ord(ch)
    return (
        0x3040 <= o <= 0x309F
        or 0x30A0 <= o <= 0x30FF
        or 0x4E00 <= o <= 0x9FFF
        or o == 0x30FC
        or o == 0x3005
    )


def _is_jp(text: str) -> bool:
    return any(_is_jp_char(ch) for ch in text)


def _norm_cmp(text: str) -> str:
    """比較用: lower + 空白/./-/除去。"""
    t = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[\s.\-/・]+", "", t)


def _canonical_base_name(canonical: str) -> str:
    head = canonical.split(".")[0].split("/")[0]
    return re.sub(r"\d+$", "", _norm_cmp(head))


def _symbol_ratio(text: str) -> float:
    if not text:
        return 0.0
    symbols = sum(
        1
        for ch in text
        if not (ch.isalnum() or _is_jp_char(ch) or ch in " \t._/-#+")
    )
    return symbols / len(text)


def _load_denylist() -> frozenset[str]:
    if not DENYLIST_PATH.exists():
        return frozenset()
    data = json.loads(DENYLIST_PATH.read_text(encoding="utf-8"))
    words: set[str] = set()
    if isinstance(data, list):
        for w in data:
            words.add(str(w).strip().lower())
    else:
        for vals in data.values():
            for w in vals:
                words.add(str(w).strip().lower())
    return frozenset(words)


def _load_canonical_skills() -> frozenset[str]:
    data = json.loads(BASE_ALIASES_PATH.read_text(encoding="utf-8"))
    return frozenset(str(s) for s in data.get("canonical_skills", []))


def _check_r12(key: str, canonical: str) -> tuple[str | None, str | None]:
    """R12: 包含判定 + 短canonical完全一致 + 先頭以外包含禁止。"""
    key_n = _norm_cmp(key)
    canon_n = _norm_cmp(canonical)
    base = _canonical_base_name(canonical)

    if key_n == canon_n:
        return None, None

    if len(base) <= 2:
        return "R12", f"短canonical={canonical}の完全一致のみ"

    if base in key_n:
        if not key_n.startswith(base):
            return "R12", "canonicalがキー先頭以外からの包含"
        return None, None

    if canon_n in key_n:
        if not key_n.startswith(canon_n):
            return "R12", "canonicalがキー先頭以外からの包含"
        return None, None

    if key_n in canon_n:
        return None, None

    return "R12", f"canonical={canonical}がキーの部分文字列でない"


def _apply_rules(
    key: str,
    canonical: str,
    denylist: frozenset[str],
    canonical_skills: frozenset[str],
) -> tuple[str | None, str | None]:
    """(CODE, note) or (None, None) if passed."""
    key_lower = key.lower()

    # A1: R9許可リストは R1〜R3 をスキップ
    skip_early = key_lower in _R9_ALLOWLIST

    if not skip_early:
        if _is_jp(key) and _JOSHI_RE.search(key):
            return "R1", "助詞含み"
        if _CONJUNCTION_START_RE.match(key):
            return "R1", "接続詞先頭"

        jp_chars = sum(1 for ch in key if _is_jp_char(ch))
        en_chars = len(key) - jp_chars
        spaces = key.count(" ")
        if jp_chars > _JP_MAX:
            return "R2", f"日本語{jp_chars}字超"
        if en_chars > _EN_MAX and not jp_chars:
            return "R2", f"英数{en_chars}字超"
        if spaces >= _SPACE_REJECT_THRESHOLD:
            return "R2", f"空白{spaces}個以上"
        if _symbol_ratio(key) >= 0.30:
            return "R2", f"記号率{_symbol_ratio(key):.0%}"

        if _NOISE_CHARS_RE.search(key) and key_lower not in _R3_ALLOWLIST:
            return "R3", "求人ノイズ記号含み"

    # R15: 未閉じ括弧・カンマ
    if _PAREN_COMMA_RE.search(key):
        return "R15", "括弧/カンマ含み"

    if canonical in _DANGER_CANONICALS:
        return "R4", f"危険canonical={canonical}"

    for prefix in _CLOUD_PREFIXES:
        if key.startswith(prefix) and len(key) > len(prefix):
            return "R5", f"クラウド子サービス(prefix={prefix.strip()})"

    if key_lower in _R6_EXTRA:
        return "R6", "職種/資格語"
    if key_lower in denylist:
        return "R6", "denylist該当"

    if not skip_early:
        if re.match(r"^[a-z0-9#+\-\.]+$", key_lower) and len(key_lower) <= 4:
            if key_lower not in _R9_ALLOWLIST:
                return "R9", f"短英字キー({key_lower})"

    if _RECRUIMENT_WORDS_RE.search(key):
        return "R13", "求人文脈語含み"

    if _EXP_SUFFIX_RE.search(key):
        return "SKIP_EXP", "経験/経験者末尾(Phase3で処理)"

    # R16: canonical が canonical_skills に無い → review
    if canonical not in canonical_skills:
        return "R16", f"未登録canonical={canonical}"

    return _check_r12(key, canonical)


def run_filter() -> None:
    with BASE_ALIASES_PATH.open(encoding="utf-8") as f:
        base = json.load(f)
    with EXPANDED_ALIASES_PATH.open(encoding="utf-8") as f:
        expanded = json.load(f)

    base_aliases: dict[str, str] = base.get("aliases", {})
    expanded_aliases: dict[str, str] = expanded.get("aliases", {})
    diff = {k: v for k, v in expanded_aliases.items() if k not in base_aliases}

    denylist = _load_denylist()
    canonical_skills = _load_canonical_skills()

    passed: dict[str, str] = {}
    rejected: list[dict[str, str]] = []
    review: list[dict[str, str]] = []
    skip_exp: list[dict[str, str]] = []
    r5_new_canonical: list[dict[str, str]] = []

    for key, canonical in sorted(diff.items()):
        code, note = _apply_rules(key, canonical, denylist, canonical_skills)
        if code is None:
            passed[key] = canonical
        elif code == "R5":
            r5_new_canonical.append({"alias_key": key, "suggested_canonical": canonical, "reason": note or ""})
        elif code == "R16":
            review.append({"key": key, "canonical": canonical, "review_code": code, "note": note or ""})
        elif code == "SKIP_EXP":
            skip_exp.append({"key": key, "canonical": canonical, "note": note or ""})
        elif code == "R12":
            review.append({"key": key, "canonical": canonical, "review_code": code, "note": note or ""})
        else:
            rejected.append({"key": key, "canonical": canonical, "reject_code": code, "note": note or ""})

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    out_filtered = OUTPUT_DIR / "alias_candidates_filtered.json"
    with out_filtered.open("w", encoding="utf-8") as f:
        json.dump({"count": len(passed), "aliases": passed}, f, ensure_ascii=False, indent=2)

    out_rejected = OUTPUT_DIR / "alias_rejected_report.csv"
    with out_rejected.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["key", "canonical", "reject_code", "note"])
        writer.writeheader()
        writer.writerows(rejected)

    out_review = OUTPUT_DIR / "review_queue.csv"
    with out_review.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["key", "canonical", "review_code", "note"])
        writer.writeheader()
        writer.writerows(review)

    out_new = OUTPUT_DIR / "new_canonical_candidates.csv"
    with out_new.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["alias_key", "suggested_canonical", "reason"])
        writer.writeheader()
        writer.writerows(r5_new_canonical)

    out_skip = OUTPUT_DIR / "skip_exp_report.csv"
    with out_skip.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["key", "canonical", "note"])
        writer.writeheader()
        writer.writerows(skip_exp)

    print(f"入力差分: {len(diff)}件")
    print(f"  通過 (filtered): {len(passed)}件 → {out_filtered}")
    print(f"  REJECT:          {len(rejected)}件 → {out_rejected}")
    print(f"  REVIEW:          {len(review)}件 → {out_review}")
    print(f"  SKIP_EXP:        {len(skip_exp)}件 → {out_skip}")
    print(f"  R5振替:          {len(r5_new_canonical)}件 → {out_new}")

    codes = Counter(r["reject_code"] for r in rejected)
    print("\nREJECT内訳:")
    for code, cnt in sorted(codes.items()):
        print(f"  {code}: {cnt}件")


if __name__ == "__main__":
    run_filter()
