from __future__ import annotations

import json
from pathlib import Path

from templates import IKOUKAKUNIN_SUBJECT, IKOUKAKUNIN_TEMPLATE, skill_format

BASE_DIR = Path(__file__).resolve().parent
WORK_DIR = BASE_DIR.parent
RESULT_PATH = WORK_DIR / "matching_v2" / "result.json"
DRAFT_DIR = BASE_DIR / "drafts"


def _read_json(path: Path) -> list[dict]:
    try:
        if not path.exists() or path.stat().st_size == 0:
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        print(f"[Step1] result.json読込エラー: {exc}", flush=True)
        return []


def _skills(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, dict):
        return [str(k) for k in value.keys()]
    return []


def _candidate_name(candidate: dict) -> str:
    return candidate.get("name") or candidate.get("engineer_name") or candidate.get("engineer_id") or "候補者"


def _candidate_id(candidate: dict) -> str:
    return str(candidate.get("engineer_id") or candidate.get("id") or _candidate_name(candidate)).replace("/", "_")


def generate_intent_drafts(result_path: Path = RESULT_PATH) -> list[dict]:
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    generated = []
    for project in _read_json(result_path):
        project_id = str(project.get("project_id") or project.get("id") or "project").replace("/", "_")
        required = _skills(project.get("required_skills") or project.get("required"))
        preferred = _skills(project.get("preferred_skills") or project.get("optional"))
        for candidate in project.get("candidates") or []:
            name = _candidate_name(candidate)
            price = candidate.get("proposed_price") or candidate.get("price") or project.get("budget") or ""
            subject = IKOUKAKUNIN_SUBJECT.format(candidate_name=name, role_area=project.get("location", ""))
            body = IKOUKAKUNIN_TEMPLATE.format(
                affiliation=candidate.get("affiliation") or "ご所属会社",
                contact_name=candidate.get("contact_name") or "ご担当者",
                project_name=project.get("project_name") or "案件名未設定",
                description=project.get("description") or project.get("project_url") or "",
                required_skills=", ".join(required) if required else "確認中",
                preferred_skills=", ".join(preferred) if preferred else "確認中",
                proposed_price=price,
                period=project.get("period") or project.get("start_date") or "確認中",
                location=project.get("location") or "確認中",
                remote=project.get("remote") or "確認中",
                interview_count=project.get("interview_count") or "確認中",
                foreign_ok="可" if project.get("foreign_ok") else "確認中",
                required_format=skill_format(required),
                preferred_format=skill_format(preferred),
            )
            path = DRAFT_DIR / f"ikoukakunin_{project_id}_{_candidate_id(candidate)}.txt"
            path.write_text(f"Subject: {subject}\nTo: {candidate.get('contact_email', '')}\n\n{body}", encoding="utf-8")
            generated.append({"path": str(path), "project": project, "candidate": candidate, "subject": subject})
    print(f"[Step1] 意向確認メール生成: {len(generated)}件", flush=True)
    return generated


if __name__ == "__main__":
    generate_intent_drafts()
