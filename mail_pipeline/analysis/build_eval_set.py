"""3000件層化抽出評価セット生成スクリプト。raw_inbox.db から抽出して JSON 出力。"""

from __future__ import annotations

import json
import random
import sqlite3
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analyze_final import classify_by_rule_explain

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "raw_inbox.db"
OUT_PATH = Path(__file__).resolve().parent / "eval_set_3000.json"

_ENGINEER_STRONG_KW = ["要員", "経歴書", "スキルシート", "並行営業可", "提案可", "人材配信"]
_PROJECT_STRONG_KW = ["案件", "単価", "面談", "募集枠", "業務内容"]
_AMBIGUOUS_KW = ["稼働", "SE経験", "PMO人材", "常駐可"]


def _has_kw(text: str, kws: list[str]) -> bool:
    return any(kw in text for kw in kws)


def build_eval_set(
    target: int = 3000,
    db_path: Path | None = None,
    seed: int = 42,
) -> list[dict]:
    """raw_inbox.db から層化抽出して評価セットを生成する。"""
    random.seed(seed)
    path = db_path or DB_PATH

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, message_id, sender, subject, body_text, classify_result "
        "FROM raw_emails ORDER BY id DESC"
    ).fetchall()
    conn.close()

    by_type: dict[str, list[dict]] = {"project": [], "engineer": [], "skip": [], "other": []}
    for r in rows:
        ct = r["classify_result"] or "skip"
        if ct not in by_type:
            ct = "other"
        by_type[ct].append(dict(r))

    sample_targets = {"project": 1500, "engineer": 900, "skip": 600}
    selected: list[dict] = []

    for label, count in sample_targets.items():
        pool = by_type.get(label, [])
        if not pool:
            continue

        if label == "project":
            high_risk = [r for r in pool if _has_kw(r.get("subject", "") or "", _PROJECT_STRONG_KW)]
        elif label == "engineer":
            high_risk = [r for r in pool if _has_kw(r.get("subject", "") or "", _ENGINEER_STRONG_KW)]
        else:
            high_risk = [r for r in pool if _has_kw(r.get("subject", "") or "", _AMBIGUOUS_KW)]

        non_high = [r for r in pool if r not in set(id(x) for x in high_risk)]
        non_high = [r for r in pool if not _has_kw(r.get("subject", "") or "", (
            _PROJECT_STRONG_KW if label == "project" else
            _ENGINEER_STRONG_KW if label == "engineer" else
            _AMBIGUOUS_KW
        ))]

        n_recent = int(count * 0.5)
        n_random = int(count * 0.3)
        n_high = count - n_recent - n_random

        recent = pool[:n_recent]
        past_pool = non_high[n_recent:]
        past = random.sample(past_pool, min(n_random, len(past_pool)))
        high = random.sample(high_risk, min(n_high, len(high_risk)))

        for r in recent + past + high:
            r["_sample_from"] = label
            selected.append(r)

    # 重複除去（message_id ベース）
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in selected:
        mid = r.get("message_id", "")
        if mid and mid not in seen:
            seen.add(mid)
            deduped.append(r)

    result: list[dict] = []
    for r in deduped[:target]:
        subj = r.get("subject", "") or ""
        sender = r.get("sender", "") or ""
        body = r.get("body_text", "") or ""

        verdict, meta = classify_by_rule_explain(subj, sender, body)

        contains_project = verdict == "project" or bool(meta.get("strong_proj"))
        contains_engineer = verdict == "engineer" or bool(meta.get("strong_eng"))

        if contains_project and contains_engineer:
            primary_type = "mixed"
        elif verdict in ("project", "engineer", "skip"):
            primary_type = verdict
        else:
            primary_type = "other"

        review_needed = verdict not in ("project", "engineer", "skip") or (
            meta.get("eng_score", 0) > 0 and meta.get("proj_score", 0) > 0
        )

        result.append(
            {
                "message_id": r.get("message_id", ""),
                "subject": subj,
                "sender": sender,
                "body_head": body[:200],
                "original_classify_result": r.get("classify_result"),
                "rule_verdict": verdict,
                "contains_project": contains_project,
                "contains_engineer": contains_engineer,
                "primary_type": primary_type,
                "review_needed": review_needed,
                "rule_meta": {
                    "eng_score": meta.get("eng_score", 0),
                    "proj_score": meta.get("proj_score", 0),
                },
            }
        )

    OUT_PATH.parent.mkdir(exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    total = len(result)
    ct = Counter(r["primary_type"] for r in result)
    print(f"生成完了: {total}件 → {OUT_PATH}")
    for k, v in sorted(ct.items()):
        print(f"  {k}: {v}件")

    return result


if __name__ == "__main__":
    build_eval_set()
