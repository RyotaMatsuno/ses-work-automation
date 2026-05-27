from __future__ import annotations

from typing import Any


def to_price(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("万円", "").replace(",", "").strip()
    return float(text) if text else 0.0


def normalize_skill(skill: str) -> str:
    return skill.strip().lower().replace(" ", "").replace("　", "")


def engineer_skill_text(engineer: dict[str, Any]) -> str:
    skills = engineer.get("skills", [])
    if isinstance(skills, list):
        return " ".join(str(skill) for skill in skills).lower()
    return str(skills).lower()


def has_skill(engineer: dict[str, Any], skill: str) -> bool:
    target = normalize_skill(skill)
    if not target:
        return True
    normalized_text = normalize_skill(engineer_skill_text(engineer))
    return target in normalized_text


def calculate_match(project: dict[str, Any], engineer: dict[str, Any]) -> dict[str, Any] | None:
    project_price = to_price(project.get("price"))
    engineer_price = to_price(engineer.get("price"))
    if project_price <= 0 or engineer_price <= 0:
        return None

    gross_profit = project_price - engineer_price
    if gross_profit < 5:
        return None

    required_skills = project.get("required_skills", []) or []
    optional_skills = project.get("optional_skills", []) or []
    required_match = {skill: has_skill(engineer, skill) for skill in required_skills}
    if not all(required_match.values()):
        return None

    optional_match = {skill: has_skill(engineer, skill) for skill in optional_skills}
    optional_rate = (
        sum(1 for matched in optional_match.values() if matched) / len(optional_match)
        if optional_match
        else 0.0
    )
    gross_profit_score = min(max((gross_profit - 5) / 2, 0), 1)
    score = 100 + optional_rate * 20 + gross_profit_score * 10

    return {
        "name": engineer.get("name", ""),
        "price": engineer_price,
        "gross_profit": gross_profit,
        "score": round(score, 2),
        "required_match": required_match,
        "optional_match": optional_match,
        "engineer": engineer,
    }


def match_projects(
    projects: list[dict[str, Any]],
    engineers: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    matched_items: list[dict[str, Any]] = []
    for project in projects:
        candidates = [
            match
            for engineer in engineers
            if (match := calculate_match(project, engineer)) is not None
        ]
        candidates.sort(
            key=lambda item: (item["score"], item["gross_profit"], -item["price"]),
            reverse=True,
        )
        top_candidates = candidates[:limit]
        if top_candidates:
            matched_items.append({"project": project, "candidates": top_candidates})
    return matched_items


def main() -> None:
    projects = [
        {
            "name": "Java開発案件",
            "price": 70,
            "required_skills": ["Java", "Spring"],
            "optional_skills": ["AWS"],
        }
    ]
    engineers = [
        {"name": "山田太郎", "price": 63, "skills": ["Java", "Spring Boot", "AWS"]},
        {"name": "佐藤花子", "price": 66, "skills": ["Java", "Spring"]},
        {"name": "田中一郎", "price": 60, "skills": ["PHP", "Laravel"]},
    ]
    matches = match_projects(projects, engineers)
    print(f"マッチ案件数: {len(matches)}")
    for item in matches:
        print(f"案件: {item['project']['name']}")
        for candidate in item["candidates"]:
            print(
                f"- {candidate['name']} 粗利:{candidate['gross_profit']} "
                f"score:{candidate['score']}"
            )


if __name__ == "__main__":
    main()
