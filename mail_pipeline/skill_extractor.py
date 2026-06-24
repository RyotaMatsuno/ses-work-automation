"""Rule-first skill extraction for SES project emails."""

from __future__ import annotations

import re
import unicodedata

KNOWN_SKILLS = {
    "java",
    "python",
    "go",
    "php",
    "ruby",
    "c#",
    "kotlin",
    "scala",
    "javascript",
    "typescript",
    "swift",
    "objective-c",
    "dart",
    "rust",
    "vb.net",
    "vba",
    "cobol",
    "pl/sql",
    "pl/i",
    "c++",
    "c言語",
    "perl",
    "spring",
    "spring boot",
    "django",
    "laravel",
    "rails",
    "flask",
    "react",
    "vue",
    "angular",
    "next.js",
    "nuxt",
    "node.js",
    "express",
    "flutter",
    "mybatis",
    "struts",
    "hibernate",
    "oracle",
    "mysql",
    "postgresql",
    "sql server",
    "redis",
    "dynamodb",
    "mongodb",
    "aurora",
    "sql",
    "aws",
    "azure",
    "gcp",
    "google cloud",
    "docker",
    "kubernetes",
    "terraform",
    "ansible",
    "linux",
    "windows server",
    "vmware",
    "cisco",
    "jp1",
    "zabbix",
    "nagios",
    "git",
    "jenkins",
    "jira",
    "confluence",
    "pmo",
    "pm",
    "pl",
    "se",
    "sre",
    "dba",
    "sap",
    "salesforce",
    "servicenow",
    "dynamics",
    "grandit",
    "uipath",
    "power bi",
    "tableau",
    "excel",
    "rpa",
    "fortigate",
    "splunk",
    "etl",
    "unity",
    "dataspider",
    "asteria",
    "prisma",
    "sase",
    "hulft",
    "ai",
    "ml",
}

HEADER_PATTERNS: list[tuple[str, str]] = [
    (r"(?:必要|必須)(?:スキル)?[：:\s]*(.*?)(?:\n|$)", "required"),
    (r"■必須[：:\s]*(.*?)(?:\n|$)", "required"),
    (r"【必要スキル】(.*?)(?:\n|$)", "required"),
    (r"【必須】(.*?)(?:\n|$)", "required"),
    (r"(?:尚可|歓迎)(?:スキル)?[：:\s]*(.*?)(?:\n|$)", "optional"),
    (r"【尚可】(.*?)(?:\n|$)", "optional"),
]

SKILL_ALIASES: dict[str, str] = {
    "java": "Java",
    "python": "Python",
    "php": "PHP",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "c#": "C#",
    "node.js": "Node.js",
    "react": "React",
    "aws": "AWS",
    "go": "Go",
    "ruby": "Ruby",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "vue": "Vue.js",
    "angular": "Angular",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "gcp": "GCP",
    "azure": "Azure",
    "spring": "Spring",
    "spring boot": "Spring",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "oracle": "Oracle",
    "mongodb": "MongoDB",
    "linux": "Linux",
    "html/css": "JavaScript",
    "fortigate": "インフラ",
    "cisco": "インフラ",
    "hulft": "インフラ",
    "jp1": "インフラ",
    "splunk": "インフラ",
    "servicenow": "インフラ",
    "etl": "インフラ",
    "terraform": "インフラ",
    "unity": "C#",
    "dataspider": "インフラ",
    "asteria": "インフラ",
    "sap": "インフラ",
    "prisma": "インフラ",
    "sase": "インフラ",
}


def extract_skills(subject: str, body: str) -> dict:
    """Extract required/optional skills from subject and body."""
    required: set[str] = set()
    optional: set[str] = set()

    subject_norm = unicodedata.normalize("NFKC", subject or "")
    text = unicodedata.normalize("NFKC", f"{subject_norm} {(body or '')[:2000]}")
    header_hit = False

    for pattern, kind in HEADER_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            found = _split_skills(match.group(1))
            if not found:
                continue
            header_hit = True
            if kind == "required":
                required.update(found)
            else:
                optional.update(found)

    # Subject bracket lists: 【React, TypeScript, AWS】 or [Java/Spring]
    for match in re.finditer(r"[【\[]([^\]】]+)[\]】]", subject_norm):
        chunk = match.group(1)
        if _looks_like_skill_list(chunk):
            required.update(_split_skills(chunk.replace("/", ",")))

    # Slash/comma skill tokens in subject (e.g. PM,PMO Java/GO)
    if subject_norm:
        for token in re.split(r"[/|｜]", subject_norm):
            token = token.strip()
            if token and _is_known_skill_token(token):
                required.add(token.lower())

    text_lower = text.lower()
    if not header_hit:
        for skill in sorted(KNOWN_SKILLS, key=len, reverse=True):
            if skill in text_lower:
                required.add(skill)

    source = "header" if header_hit else ("dictionary" if required or optional else "none")
    return {
        "required": sorted(required),
        "optional": sorted(optional),
        "source": source,
    }


def _looks_like_skill_list(chunk: str) -> bool:
    lower = chunk.lower()
    if any(skill in lower for skill in KNOWN_SKILLS):
        return True
    if re.search(r"(?:react|java|python|aws|vue|typescript|kotlin|sql|pmo|pm\b)", lower):
        return True
    return "," in chunk or "、" in chunk


def _is_known_skill_token(token: str) -> bool:
    cleaned = re.sub(r"[\d万円~〜\-]+", "", token).strip().lower()
    if not cleaned or len(cleaned) > 40:
        return False
    if cleaned in KNOWN_SKILLS:
        return True
    return any(skill in cleaned for skill in ("java", "react", "vue", "python", "aws", "pmo", "go", "sql"))


def normalize_to_valid_skills(skills: list[str], valid_skills: list[str]) -> list[str]:
    """Map extracted skill names to Notion VALID_SKILLS entries."""
    valid_lower = {s.lower(): s for s in valid_skills}
    out: list[str] = []
    seen: set[str] = set()
    for raw in skills:
        key = raw.strip().lower()
        if not key:
            continue
        mapped = valid_lower.get(key) or SKILL_ALIASES.get(key)
        if not mapped:
            for valid in valid_skills:
                if valid.lower() in key or key in valid.lower():
                    mapped = valid
                    break
        if mapped and mapped not in seen:
            seen.add(mapped)
            out.append(mapped)
    return out


def merge_extracted_skills(
    ai_required: list[str],
    ai_optional: list[str],
    subject: str,
    body: str,
    valid_skills: list[str],
) -> tuple[list[str], list[str]]:
    """Merge AI and rule-based skills, normalized to VALID_SKILLS."""
    rule_result = extract_skills(subject, body)
    merged_required = list({*(s.lower() for s in ai_required), *rule_result["required"]})
    merged_optional = list({*(s.lower() for s in ai_optional), *rule_result["optional"]})
    req = normalize_to_valid_skills(merged_required, valid_skills)
    opt = normalize_to_valid_skills(merged_optional, valid_skills)
    opt = [s for s in opt if s not in req]
    return req, opt


def _split_skills(text: str) -> set[str]:
    parts = re.split(r"[,、/|・\n　]", text)
    result: set[str] = set()
    for part in parts:
        part = part.strip()
        if not part:
            continue
        part = re.sub(r"[(（][^)）]*[)）]", "", part).strip()
        part = re.sub(r"\d+年以上", "", part).strip()
        if part:
            result.add(part.lower())
    return result
