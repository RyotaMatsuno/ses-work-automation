from __future__ import annotations

from typing import Any

from matcher import to_price


def format_price(value: Any) -> str:
    price = to_price(value)
    return str(int(price)) if price.is_integer() else str(price)


def skill_form(title: str, skills: list[str]) -> str:
    lines = [title]
    if not skills:
        lines.append(" □ 記載なし：")
    else:
        lines.extend(f" □ {skill}：" for skill in skills)
    return "\n".join(lines)


def calculate_offer_price(engineer: dict[str, Any]) -> float:
    return to_price(engineer.get("price")) + 7


def first_text_value(source: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value not in (None, "", []):
            return str(value)
    return ""


def compose_draft(project: dict[str, Any], candidate: dict[str, Any]) -> str:
    engineer = candidate.get("engineer", candidate)
    required_skills = project.get("required_skills", []) or []
    optional_skills = project.get("optional_skills", []) or []
    offer_price = calculate_offer_price(engineer)
    company_name = first_text_value(engineer, "所属会社", "所属会社名", "company_name") or "所属会社"
    assignee = first_text_value(engineer, "所属担当者名", "担当者名", "assignee") or "ご担当者"
    role_area = project.get("location") or project.get("name") or "案件"

    parts = [
        f"件名: {engineer.get('name', '')}様 案件ご検討のお願い（{role_area}）",
        "",
        f"{company_name} {assignee}様",
        "",
        "いつもお世話になっております。",
        "人員のご紹介ありがとうございます。",
        "下記案件いかがでしょうか。",
        "",
        f"▼案件名\n{project.get('name', '')}",
        f"▼業務内容\n{project.get('detail', '') or '確認中'}",
        skill_form("▼必須スキル（○/×）", required_skills),
        skill_form("▼尚可スキル（○/×）", optional_skills),
        f"▼提案単価\n{format_price(offer_price)}万円",
        f"▼期間\n{project.get('period') or '確認中'}",
        f"▼勤務地\n{project.get('location') or '確認中'}",
        f"▼リモート\n{project.get('remote') or '確認中'}",
        f"▼面談回数\n{project.get('interviews') or '確認中'}",
        f"▼外国籍可否\n{project.get('nationality') or '確認中'}",
        "",
        "▼並行状況",
        " 例）なし",
        "",
        "何卒よろしくお願いいたします。",
    ]
    return "\n".join(parts)


def attach_drafts(matched_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in matched_items:
        project = item["project"]
        candidates = []
        for candidate in item["candidates"]:
            candidate_with_draft = dict(candidate)
            candidate_with_draft["draft_mail"] = compose_draft(project, candidate)
            candidates.append(candidate_with_draft)
        output.append({"project": project, "candidates": candidates})
    return output


def main() -> None:
    project = {
        "name": "Java開発案件",
        "price": 70,
        "required_skills": ["Java", "Spring"],
        "optional_skills": ["AWS"],
        "detail": "Webアプリケーション開発",
        "period": "即日〜長期",
        "location": "東京",
    }
    candidate = {
        "name": "山田太郎",
        "price": 63,
        "gross_profit": 7,
        "engineer": {"name": "山田太郎", "price": 63, "assignee": "佐藤"},
    }
    print(compose_draft(project, candidate))


if __name__ == "__main__":
    main()
