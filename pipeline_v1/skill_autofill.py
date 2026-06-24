from __future__ import annotations

import json
from typing import Any

import requests
from anthropic import Anthropic
from dotenv import dotenv_values
from fetcher import ENV_PATH, notion_headers

MODEL_NAME = "claude-haiku-4-5-20251001"
VALID_SKILLS = {
    "Java",
    "Python",
    "PHP",
    "JavaScript",
    "TypeScript",
    "C#",
    "C++",
    "Go",
    "Ruby",
    "Swift",
    "Kotlin",
    "React",
    "Vue.js",
    "Angular",
    "Next.js",
    "Node.js",
    "Spring Boot",
    "Django",
    "Flask",
    "Laravel",
    "AWS",
    "GCP",
    "Azure",
    "Docker",
    "Kubernetes",
    "Linux",
    "MySQL",
    "PostgreSQL",
    "Oracle",
    "SQL Server",
    "MongoDB",
    "Redis",
    "Git",
    "Terraform",
    "Ansible",
    "Jenkins",
    "Salesforce",
    "SAP",
    "PowerBI",
    "Tableau",
    "Spark",
    "TensorFlow",
    "CCNA",
    "Cisco",
}

SYSTEM_PROMPT = """SES案件テキストからスキルを抽出してJSON形式で返してください。
Reply JSON only. No markdown.
{"required_skills": ["Java", "Spring Boot"], "optional_skills": ["Docker"]}
スキル名は英語（Java, Python, AWS, Reactなど）で返してください。
不明な場合は空リスト。"""


def load_anthropic_api_key() -> str:
    config = dotenv_values(ENV_PATH)
    api_key = config.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(f"ANTHROPIC_API_KEY is not set in {ENV_PATH}")
    return api_key


def load_notion_api_key() -> str:
    config = dotenv_values(ENV_PATH)
    api_key = config.get("NOTION_API_KEY")
    if not api_key:
        raise RuntimeError(f"NOTION_API_KEY is not set in {ENV_PATH}")
    return api_key


def normalize_skills(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    seen: set[str] = set()
    skills: list[str] = []
    for item in value:
        skill = str(item).strip()
        if skill in VALID_SKILLS and skill not in seen:
            seen.add(skill)
            skills.append(skill)
    return skills


def parse_skill_json(text: str) -> dict[str, list[str]]:
    text = text.strip().replace("```json", "").replace("```", "").strip()
    if not text:
        return {"required_skills": [], "optional_skills": []}
    try:
        data = json.loads(text)
    except Exception:
        return {"required_skills": [], "optional_skills": []}
    if not isinstance(data, dict):
        return {"required_skills": [], "optional_skills": []}

    return {
        "required_skills": normalize_skills(data.get("required_skills")),
        "optional_skills": normalize_skills(data.get("optional_skills")),
    }


def extract_skills(detail_text: str, api_key: str) -> dict[str, list[str]]:
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": detail_text}],
    )
    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    try:
        return parse_skill_json("".join(text_parts))
    except Exception as e:
        print(f"[skill_autofill] parse error: {e}")
        return {"required_skills": [], "optional_skills": []}


def patch_project_skills(
    page_id: str,
    required_skills: list[str],
    optional_skills: list[str],
    notion_api_key: str,
) -> None:
    props: dict[str, Any] = {}
    if required_skills:
        props["必要スキル"] = {"multi_select": [{"name": skill} for skill in required_skills]}
    if optional_skills:
        props["尚可スキル"] = {"multi_select": [{"name": skill} for skill in optional_skills]}
    if not props:
        return

    response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=notion_headers(notion_api_key),
        json={"properties": props},
        timeout=30,
    )
    response.raise_for_status()


def should_autofill(project: dict[str, Any]) -> bool:
    return (
        not project.get("required_skills")
        and not project.get("optional_skills")
        and bool(project.get("detail"))
        and bool(project.get("id"))
    )


def autofill_skills(projects: list[dict[str, Any]], api_key: str) -> list[dict[str, Any]]:
    """スキル空案件のdetailからスキルを抽出してNotionに書き戻し、projectsを更新して返す"""
    notion_api_key = load_notion_api_key()

    for project in projects:
        if not should_autofill(project):
            continue

        extracted = extract_skills(project["detail"], api_key)
        required_skills = extracted["required_skills"]
        optional_skills = extracted["optional_skills"]
        patch_project_skills(
            project["id"],
            required_skills,
            optional_skills,
            notion_api_key,
        )
        project["required_skills"] = required_skills
        project["optional_skills"] = optional_skills

    return projects
