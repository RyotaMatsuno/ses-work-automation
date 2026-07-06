"""BH: 提示単価レンジ補完エンジン。

明示単価のない案件に対して、過去の明示単価案件の分布から
参考単価レンジを推定して返す。マッチングスコアには反映しない。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
RULES_PATH = BASE_DIR / "price_rules.json"

# 判断マニュアルv3 適正単価テーブル（フォールバック）
_MANUAL_FALLBACK: dict[str, tuple[float, float]] = {
    "senior_se": (75.0, 80.0),   # 上級SE（要件定義〜）
    "se": (65.0, 70.0),          # SE（基本設計〜）
    "senior_pg": (55.0, 60.0),   # 上級PG（詳細設計〜）
    "pg": (45.0, 50.0),          # PG（製造中心）
    "pmo": (60.0, 70.0),
    "infra": (60.0, 70.0),
    "test": (40.0, 50.0),
    "helpdesk": (35.0, 45.0),
    "other": (50.0, 65.0),
}

_ROLE_RE = re.compile(
    r"(?P<pmo>PMO|PM補佐|社内SE)|"
    r"(?P<infra>インフラ|NW|ネットワーク|サーバー|クラウド|AWS|Azure|GCP)|"
    r"(?P<test>テスト|QA|検証)|"
    r"(?P<helpdesk>ヘルプデスク|コールセンター|キッティング|情シス)|"
    r"(?P<senior_se>要件定義|上流|アーキテクト|PL|テックリード)|"
    r"(?P<se>基本設計|詳細設計|SE|システム開発)|"
    r"(?P<senior_pg>詳細設計|PG|プログラマー)|"
    r"(?P<pg>製造|コーディング|実装)",
    re.IGNORECASE,
)


def _detect_role(case_info: dict[str, Any]) -> str:
    """案件情報からロールを推定する。"""
    job_cat = str(case_info.get("job_category") or "").lower()
    if job_cat in ("pmo",):
        return "pmo"
    if job_cat in ("infrastructure", "infra"):
        return "infra"
    if job_cat in ("testing", "test"):
        return "test"
    if job_cat in ("helpdesk",):
        return "helpdesk"

    text = " ".join([
        str(case_info.get("name") or ""),
        str(case_info.get("note") or ""),
        str(case_info.get("role") or ""),
    ])
    m = _ROLE_RE.search(text)
    if m:
        for role_key in ("pmo", "infra", "test", "helpdesk", "senior_se", "se", "senior_pg", "pg"):
            if m.group(role_key):
                return role_key
    return "other"


def estimate_price(case_info: dict[str, Any]) -> dict[str, Any]:
    """単価未設定案件の参考単価レンジを推定する。

    Returns:
        {
            "estimated_min": float | None,
            "estimated_max": float | None,
            "confidence_rank": "high" | "medium" | "low",
            "method": str,
        }
    """
    rules = _load_rules()
    role = _detect_role(case_info)

    # price_rules.json から参照
    if rules and role in rules:
        entry = rules[role]
        n = entry.get("n", 0)
        est_min = entry.get("p25") or entry.get("min")
        est_max = entry.get("p75") or entry.get("max")
        if est_min is not None and est_max is not None:
            if n >= 30:
                confidence = "high"
            elif n >= 10:
                confidence = "medium"
            else:
                confidence = "low"
            return {
                "estimated_min": float(est_min),
                "estimated_max": float(est_max),
                "confidence_rank": confidence,
                "method": f"rules/{role}(n={n})",
            }

    # フォールバック: 判断マニュアルv3 適正単価テーブル
    fallback = _MANUAL_FALLBACK.get(role) or _MANUAL_FALLBACK["other"]
    return {
        "estimated_min": fallback[0],
        "estimated_max": fallback[1],
        "confidence_rank": "low",
        "method": f"manual_fallback/{role}",
    }


def _load_rules() -> dict[str, Any]:
    if RULES_PATH.exists():
        try:
            with RULES_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("price_rules.json 読み込み失敗: %s", exc)
    return {}


def build_price_rules(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """明示単価あり案件から階層統計を構築して price_rules.json に保存する。

    cases: 各要素に budget_min, budget_max, job_category, role などを持つ dict のリスト。
    """
    import statistics

    by_role: dict[str, list[float]] = {}
    for case in cases:
        bmin = case.get("budget_min") or case.get("price_min")
        bmax = case.get("budget_max") or case.get("price_max")
        if bmin is None and bmax is None:
            continue
        mid = (
            ((bmin or 0) + (bmax or 0)) / 2
            if bmin is not None and bmax is not None
            else (bmin or bmax)
        )
        if not mid or mid < 20 or mid > 200:
            continue
        role = _detect_role(case)
        by_role.setdefault(role, []).append(float(mid))

    # IQR 外れ値除去
    rules: dict[str, Any] = {}
    for role, prices in by_role.items():
        if len(prices) < 3:
            continue
        sorted_p = sorted(prices)
        n = len(sorted_p)
        q1 = sorted_p[n // 4]
        q3 = sorted_p[3 * n // 4]
        iqr = q3 - q1
        filtered = [p for p in sorted_p if q1 - 1.5 * iqr <= p <= q3 + 1.5 * iqr]
        if len(filtered) < 3:
            filtered = sorted_p
        nf = len(filtered)
        rules[role] = {
            "n": nf,
            "min": round(min(filtered), 1),
            "max": round(max(filtered), 1),
            "mean": round(statistics.mean(filtered), 1),
            "median": round(statistics.median(filtered), 1),
            "p25": round(filtered[nf // 4], 1),
            "p75": round(filtered[3 * nf // 4], 1),
        }

    with RULES_PATH.open("w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    logger.info("price_rules.json 生成完了: %d ロール", len(rules))
    return rules
