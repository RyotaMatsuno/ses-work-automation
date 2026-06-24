from __future__ import annotations

import json
from pathlib import Path

from dotenv import dotenv_values

from templates import CANDIDATE_TEMPLATE, PROPOSAL_TEMPLATE

BASE_DIR = Path(__file__).resolve().parent
WORK_DIR = BASE_DIR.parent
ENV_PATH = WORK_DIR / "config" / ".env"
RESULT_PATH = WORK_DIR / "matching_v2" / "result.json"
DRAFT_DIR = BASE_DIR / "drafts"


def _read_projects() -> list[dict]:
    try:
        if RESULT_PATH.exists():
            data = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception as exc:
        print(f"[Step5] result.json読込エラー: {exc}", flush=True)
    return []


def _skill_summary(value) -> str:
    if isinstance(value, dict):
        return (
            ", ".join(f"{k}:{v.get('result', v)}" if isinstance(v, dict) else f"{k}:{v}" for k, v in value.items())
            or "確認中"
        )
    if isinstance(value, list):
        return ", ".join(map(str, value)) or "確認中"
    return "確認中"


def _summary(project: dict, candidates: list[dict]) -> str:
    cfg = dotenv_values(str(ENV_PATH))
    if cfg.get("ANTHROPIC_API_KEY"):
        names = "、".join(c.get("engineer_name") or c.get("name") or "候補者" for c in candidates)
        return f"{project.get('project_name', '対象案件')}に対し、{names}をスキル適合度と単価バランスで選定しました。"
    return "候補者のスキル適合度、単価、稼働開始時期を踏まえて提案候補を選定しました。"


def generate_proposals() -> list[dict]:
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = []
    labels = ["松", "竹", "梅"]
    for project in _read_projects():
        candidates = sorted(project.get("candidates") or [], key=lambda c: c.get("score", 0), reverse=True)[:3]
        if not candidates:
            continue
        blocks = []
        for idx, candidate in enumerate(candidates):
            blocks.append(
                CANDIDATE_TEMPLATE.format(
                    rank_label=labels[idx],
                    name=candidate.get("engineer_name") or candidate.get("name") or "候補者",
                    price=candidate.get("proposed_price") or candidate.get("price") or "確認中",
                    available_date=candidate.get("available_date") or "確認中",
                    required=_skill_summary(candidate.get("required") or candidate.get("required_match")),
                    preferred=_skill_summary(candidate.get("optional") or candidate.get("preferred_match")),
                    appeal=f"マッチングスコア {candidate.get('score', '確認中')}",
                )
            )
        body = PROPOSAL_TEMPLATE.format(
            project_name=project.get("project_name") or "案件名未設定",
            candidate_blocks="\n".join(blocks),
            summary=_summary(project, candidates),
        )
        project_id = str(project.get("project_id") or project.get("id") or "project").replace("/", "_")
        path = DRAFT_DIR / f"proposal_{project_id}.txt"
        path.write_text(f"Subject: {project.get('project_name', '')} ご提案\nTo: \n\n{body}", encoding="utf-8")
        outputs.append({"path": str(path), "project": project})
    print(f"[Step5] 提案文生成: {len(outputs)}件", flush=True)
    return outputs


if __name__ == "__main__":
    generate_proposals()
