from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PARSED_DIR = BASE_DIR / "parsed_replies"

STATUS_SCORES = {
    "面談調整中": 1.5,
    "面談予定": 2.0,
    "オファー中": 5.0,
}


def _result_wait_score(text: str) -> float:
    m = re.search(r"(\d+)\s*日", text)
    if not m:
        return 2.5
    days = int(m.group(1))
    if days <= 2:
        return 2.5
    if days <= 7:
        return 2.0
    if days <= 14:
        return 1.5
    return 1.0


def parallel_score(statuses: list[str]) -> float:
    total = 0.0
    for status in statuses:
        if "結果待ち" in status:
            total += _result_wait_score(status)
            continue
        for key, score in STATUS_SCORES.items():
            if key in status:
                total += score
                break
    return total


def judge_reply(data: dict) -> dict:
    score = parallel_score(data.get("parallel_status") or [])
    required = data.get("required_skills") or {}
    gross_profit = data.get("gross_profit")
    reasons = []
    if score >= 5.0:
        reasons.append("並行スコア合計5.0以上")
    if any(v == "×" for v in required.values()):
        reasons.append("必須スキルに×")
    if gross_profit is not None and gross_profit < 5:
        reasons.append("粗利5万円未満")
    data["judge"] = {
        "proposal_ok": not reasons,
        "parallel_score": score,
        "reasons": reasons,
        "judged_at": datetime.now().isoformat(),
    }
    return data


def judge_all() -> list[dict]:
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for path in sorted(PARSED_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            judged = judge_reply(data)
            path.write_text(json.dumps(judged, ensure_ascii=False, indent=2), encoding="utf-8")
            results.append(judged)
        except Exception as exc:
            print(f"[Step4] 判定エラー({path.name}): {exc}", flush=True)
    ok = sum(1 for item in results if item.get("judge", {}).get("proposal_ok"))
    ng = len(results) - ok
    print(f"[Step4] 提案可否判定: {ok}件OK / {ng}件NG", flush=True)
    return results


if __name__ == "__main__":
    judge_all()
