"""generate_precision_sample.py — 通過分から層化40件サンプル生成。

層化カテゴリ:
  - 短英字系 (10件): キーが純英数字のみ、かつ短い (≤ 10文字)
  - 和文系    (10件): キーに日本語を含む
  - クラウド系 (10件): AWS/Azure/GCP/Oracle Cloud/VMware など
  - 略語系    (10件): 2〜5文字の英字略語・バージョン付き技術名

出力: tools/output/precision_sample_40.md
"""

from __future__ import annotations

import json
import random
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
FILTERED_PATH = OUTPUT_DIR / "alias_candidates_filtered.json"
OUT_PATH = OUTPUT_DIR / "precision_sample_40.md"

CLOUD_KEYWORDS = re.compile(r"^(aws|azure|gcp|google|oracle|vmware|microsoft|nutanix|cisco|salesforce)", re.IGNORECASE)
ABBREV_RE = re.compile(r"^[a-z][a-z0-9]{1,4}$")
JP_CHAR_RE = re.compile(r"[　-鿿＀-￯]")


def _is_jp(text: str) -> bool:
    return bool(JP_CHAR_RE.search(text))


def _is_cloud(key: str) -> bool:
    return bool(CLOUD_KEYWORDS.match(key))


def _is_abbrev(key: str) -> bool:
    return bool(ABBREV_RE.match(key))


def _is_short_en(key: str) -> bool:
    return re.match(r"^[a-z0-9 .\-_/#+]+$", key) is not None and len(key) <= 10


def categorize(key: str) -> str:
    if _is_cloud(key):
        return "cloud"
    if _is_jp(key):
        return "jp"
    if _is_abbrev(key):
        return "abbrev"
    if _is_short_en(key):
        return "short_en"
    return "other"


def main() -> None:
    with FILTERED_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    aliases: dict[str, str] = data["aliases"]

    buckets: dict[str, list[tuple[str, str]]] = {
        "short_en": [],
        "jp": [],
        "cloud": [],
        "abbrev": [],
        "other": [],
    }
    for key, canonical in aliases.items():
        cat = categorize(key)
        buckets[cat].append((key, canonical))

    random.seed(20260705)
    sample: list[tuple[str, str, str]] = []

    target_buckets = [
        ("short_en", "短英字系", 10),
        ("jp",       "和文系",   10),
        ("cloud",    "クラウド系", 10),
        ("abbrev",   "略語系",   10),
    ]
    for cat, label, n in target_buckets:
        pool = buckets[cat]
        random.shuffle(pool)
        chosen = pool[:n]
        # 不足分は other から補充
        if len(chosen) < n:
            pool2 = buckets["other"]
            random.shuffle(pool2)
            extra = pool2[: n - len(chosen)]
            chosen += extra
        for key, canonical in chosen:
            sample.append((label, key, canonical))

    lines = [
        "# precision_sample_40 — alias候補 層化40件レビューシート",
        "",
        "作成: 2026-07-05 / Phase 2 停止地点 → 松野OKが出るまでPhase 4 に進まない",
        "",
        "## 判定基準",
        "- ○: このalias登録は適切（false match リスク低）",
        "- △: 微妙（Phaseリーダー判断）",
        "- ×: false match リスク高・登録不可",
        "",
        "**false match 4/40超なら基準強化してPhase 1再実行。松野OKが出るまでPhase 4に進まない。**",
        "",
        "---",
        "",
        "| # | カテゴリ | エイリアスキー | → canonical | 判定 | メモ |",
        "|---|---------|--------------|------------|------|-----|",
    ]

    for i, (label, key, canonical) in enumerate(sample, 1):
        lines.append(f"| {i} | {label} | `{key}` | {canonical} | | |")

    lines += [
        "",
        "---",
        "",
        "## 集計欄",
        "",
        "- ○: _ 件",
        "- △: _ 件",
        "- ×: _ 件",
        "",
        "false match数: _ / 40",
        "",
        "松野判定: **[ ] OK → Phase 4 実行可** / **[ ] NG → Phase 1 基準強化**",
    ]

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"precision_sample_40.md を生成しました: {OUT_PATH}")
    print("カテゴリ内訳:")
    for cat, items in buckets.items():
        print(f"  {cat}: {len(items)}件 (pool)")
    print(f"サンプル合計: {len(sample)}件")


if __name__ == "__main__":
    main()
