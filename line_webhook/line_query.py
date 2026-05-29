import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import Any

import jpholiday
import requests
from dateutil import parser
from dotenv import dotenv_values


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "config", ".env"))
CONFIG = dotenv_values(ENV_PATH)

NOTION_TOKEN = (
    CONFIG.get("NOTION_TOKEN")
    or CONFIG.get("NOTION_API_KEY")
    or os.environ.get("NOTION_TOKEN")
    or os.environ.get("NOTION_API_KEY")
    or ""
)
ENGINEER_DB_ID = (
    CONFIG.get("ENGINEER_DB_ID")
    or CONFIG.get("NOTION_ENGINEER_DB_ID")
    or os.environ.get("ENGINEER_DB_ID")
    or os.environ.get("NOTION_ENGINEER_DB_ID")
    or ""
)
PROJECT_DB_ID = (
    CONFIG.get("PROJECT_DB_ID")
    or CONFIG.get("NOTION_PROJECT_DB_ID")
    or os.environ.get("PROJECT_DB_ID")
    or os.environ.get("NOTION_PROJECT_DB_ID")
    or ""
)

NOTION_VERSION = "2022-06-28"
NOTION_QUERY_URL = "https://api.notion.com/v1/databases/{db_id}/query"
ERROR_MESSAGE = "照会中にエラーが発生しました。しばらく後に再試行してください。"
LINE_LIMIT = 5000
TOP_LIMIT = 5
GROSS_THRESHOLDS = {"松野": 5, "岡本": 3, "共通": 3}

logger = logging.getLogger(__name__)


def _notion_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
        "Notion-Version": NOTION_VERSION,
    }


def fetch_all_pages(db_id: str) -> list[dict]:
    results: list[dict] = []
    payload: dict[str, Any] = {"page_size": 100}

    while True:
        response = requests.post(
            NOTION_QUERY_URL.format(db_id=db_id),
            headers=_notion_headers(),
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        results.extend(data.get("results", []))

        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")

    return results


def business_days_since(dt) -> int:
    if isinstance(dt, str):
        start_date = parser.isoparse(dt).date()
    elif isinstance(dt, datetime):
        start_date = dt.date()
    elif isinstance(dt, date):
        start_date = dt
    else:
        raise TypeError("dt must be datetime, date, or ISO string")

    today = date.today()
    if start_date >= today:
        return 0

    days = 0
    current = start_date + timedelta(days=1)
    while current <= today:
        if current.weekday() < 5 and not jpholiday.is_holiday(current):
            days += 1
        current += timedelta(days=1)
    return days


def classify_query(text: str) -> tuple[str, dict]:
    stripped = text.strip()
    match = re.match(r"^([A-Za-z]{1,4})[\s\u3000/](.+)$", stripped)
    if match:
        return ("engineer", {"initial": match.group(1).upper(), "station": match.group(2).strip()})
    return ("project", {"name": stripped})


def skill_match(required: list[str], engineer_skills: list[str]) -> bool:
    if not required:
        return True

    engineer_lower = [skill.lower() for skill in engineer_skills if skill]
    for req in required:
        req_lower = req.lower()
        if not any(req_lower in skill for skill in engineer_lower):
            return False
    return True


def calc_gross_profit(budget: float, cost: float) -> float:
    return float(budget or 0) - float(cost or 0)


def _normalize_initial(s: str) -> str:
    import re as _re2
    return _re2.sub(r'[\s\u3000.\u30fb\u00b7]', '', s).upper()


def _match_initial(engineer: dict, initial: str) -> bool:
    _PROP_INI = 'イニシャル'
    _PROP_NAME = '名前'
    ini = _text_prop(engineer, _PROP_INI)
    if ini:
        return _normalize_initial(ini) == initial.upper()
    name = _text_prop(engineer, _PROP_NAME)
    return _normalize_initial(name) == initial.upper()


def _match_station(engineer: dict, station: str) -> bool:
    _PROP_STA = '最寄り駅'
    _PROP_MEMO = '備考（LINEメモ）'
    if not station:
        return True
    sta = _text_prop(engineer, _PROP_STA)
    if sta:
        return station in sta
    memo = _text_prop(engineer, _PROP_MEMO)
    if memo and station in memo:
        return True
    return True  # no station data -> match by initial only



def engineer_query(initial: str, station: str) -> str:
    engineers = fetch_all_pages(ENGINEER_DB_ID)
    matched_engineers = [
        engineer
        for engineer in engineers
        if _match_initial(engineer, initial)
        and _match_station(engineer, station)
    ]

    if not matched_engineers:
        return f"一致する人員が見つかりませんでした: {initial} {station}"

    projects = fetch_all_pages(PROJECT_DB_ID)
    replies = []
    for engineer in matched_engineers:
        engineer_skills = _multi_select_prop(engineer, "スキル")
        engineer_rate = _number_prop(engineer, "単価（万円）")
        matched_projects = []

        for project in projects:
            if _select_prop(project, "ステータス") != "募集中":
                continue
            if business_days_since(project.get("last_edited_time")) > 4:
                continue
            required = _multi_select_prop(project, "必要スキル")
            if not skill_match(required, engineer_skills):
                continue

            budget = _number_prop(project, "単価（万円）")
            gross = calc_gross_profit(budget, engineer_rate)
            if gross < _gross_threshold(_select_prop(project, "担当者")):
                continue

            matched_projects.append({"page": project, "gross_profit": gross})

        matched_projects.sort(key=lambda item: item["gross_profit"], reverse=True)
        replies.append(format_project_result(engineer, matched_projects))

    return "\n\n".join(replies)


def project_query(name: str) -> str:
    projects = fetch_all_pages(PROJECT_DB_ID)
    matched_projects = [
        project
        for project in projects
        if _contains(_text_prop(project, "案件名"), name)
        and _select_prop(project, "ステータス") == "募集中"
    ]

    if not matched_projects:
        return f"一致する案件が見つかりませんでした: {name}"

    project = matched_projects[0]
    required = _multi_select_prop(project, "必要スキル")
    budget = _number_prop(project, "単価（万円）")
    threshold = _gross_threshold(_select_prop(project, "担当者"))
    engineers = fetch_all_pages(ENGINEER_DB_ID)
    matched_engineers = []

    for engineer in engineers:
        if _select_prop(engineer, "稼働状況") not in ["稼働可能", "調整中"]:
            continue
        if business_days_since(engineer.get("last_edited_time")) > 21:
            continue
        engineer_skills = _multi_select_prop(engineer, "スキル")
        if not skill_match(required, engineer_skills):
            continue

        gross = calc_gross_profit(budget, _number_prop(engineer, "単価（万円）"))
        if gross < threshold:
            continue

        matched_engineers.append({"page": engineer, "gross_profit": gross})

    matched_engineers.sort(key=lambda item: item["gross_profit"], reverse=True)
    return format_engineer_result(project, matched_engineers)


def format_project_result(engineer: dict, projects: list) -> str:
    initial = _text_prop(engineer, 'イニシャル') or _text_prop(engineer, '名前')
    station = _text_prop(engineer, '最寄り駅')
    if not projects:
        return (
            f"【{initial}｜{station}】マッチ案件なし\n"
            "（条件: 有効案件なし or スキル・粗利不一致）"
        )

    lines = [f"【{initial}｜{station}】マッチ案件 {len(projects)}件"]
    for index, item in enumerate(projects, 1):
        project = item["page"]
        lines.extend(
            [
                "",
                "━━━━━━━━━━━━",
                f"{_num_label(index)}{_text_prop(project, '案件名')}",
                "━━━━━━━━━━━━",
                f"業務内容  : {_text_prop(project, '案件詳細')}",
                f"必要スキル: {_join(_multi_select_prop(project, '必要スキル'))}",
                f"尚可スキル: {_join(_multi_select_prop(project, '尚可スキル'))}",
                f"勤務地    : {_text_prop(project, '勤務地')}（リモート: {_select_prop(project, 'リモート')}）",
                f"期間      : {_text_prop(project, '期間')}",
                f"面談      : {_format_number(_number_prop(project, '面談希望'))}回",
                f"提示単価  : {_format_number(_number_prop(project, '単価（万円）'))}万円",
                f"粗利      : {_format_number(item['gross_profit'])}万円",
                f"担当      : {_select_prop(project, '担当者')}",
                f"鮮度      : 最終更新{business_days_since(project.get('last_edited_time'))}日前",
            ]
        )

    return _limit_reply(lines, projects, format_project_result, engineer)


def format_engineer_result(project: dict, engineers: list) -> str:
    project_name = _text_prop(project, "案件名")
    if not engineers:
        return (
            f"【{project_name}】マッチ人員なし\n"
            "（条件: スキル・粗利・鮮度条件不一致）"
        )

    lines = [f"【{project_name}】マッチ人員 {len(engineers)}名"]
    for index, item in enumerate(engineers, 1):
        engineer = item["page"]
        lines.extend(
            [
                "",
                "━━━━━━━━━━━━",
                f"{_num_label(index)}{_text_prop(engineer, '名前')}｜{_text_prop(engineer, '最寄り駅')}",
                "━━━━━━━━━━━━",
                f"スキル    : {_join(_multi_select_prop(engineer, 'スキル'))}",
                f"稼働状況  : {_select_prop(engineer, '稼働状況')}",
                f"稼働可能日: {_date_prop(engineer, '稼働可能日') or '未設定'}",
                f"所属      : {_text_prop(engineer, '所属会社')}",
                f"希望単価  : {_format_number(_number_prop(engineer, '単価（万円）'))}万円",
                f"粗利      : {_format_number(item['gross_profit'])}万円",
                f"並行状況  : {_text_prop(engineer, '備考（LINEメモ）')[:50]}",
                f"鮮度      : 最終更新{business_days_since(engineer.get('last_edited_time'))}日前",
            ]
        )

    return _limit_reply(lines, engineers, format_engineer_result, project)


def handle_line_query(text: str) -> str | None:
    if not text or not text.strip():
        return None

    try:
        query_type, params = classify_query(text)
        if query_type == "engineer":
            return engineer_query(params["initial"], params["station"])
        return project_query(params["name"])
    except Exception:
        logger.exception("line_query failed")
        return ERROR_MESSAGE


def _prop(page: dict, name: str) -> dict:
    return page.get("properties", {}).get(name, {})


def _text_prop(page: dict, name: str) -> str:
    prop = _prop(page, name)
    prop_type = prop.get("type")
    if prop_type == "title":
        values = prop.get("title", [])
    elif prop_type == "rich_text":
        values = prop.get("rich_text", [])
    else:
        values = []
    return "".join(item.get("plain_text", "") for item in values).strip()


def _multi_select_prop(page: dict, name: str) -> list[str]:
    return [item.get("name", "") for item in _prop(page, name).get("multi_select", []) if item.get("name")]


def _select_prop(page: dict, name: str) -> str:
    value = _prop(page, name).get("select")
    return value.get("name", "") if value else ""


def _number_prop(page: dict, name: str) -> float:
    value = _prop(page, name).get("number")
    return float(value or 0)


def _date_prop(page: dict, name: str) -> str:
    value = _prop(page, name).get("date")
    return value.get("start", "") if value else ""


def _contains(value: str, keyword: str) -> bool:
    return keyword.lower() in value.lower()


def _gross_threshold(assignee: str) -> int:
    return GROSS_THRESHOLDS.get(assignee, 3)


def _join(values: list[str]) -> str:
    return " / ".join(values)


def _format_number(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _num_label(index: int) -> str:
    labels = "①②③④⑤⑥⑦⑧⑨⑩"
    if 1 <= index <= len(labels):
        return labels[index - 1]
    return f"{index}."


def _limit_reply(lines: list[str], items: list, formatter, header_page: dict) -> str:
    text = "\n".join(lines)
    if len(text) <= LINE_LIMIT:
        return text
    limited_lines = lines[:1]
    for line in lines[1:]:
        if line.startswith(f"{_num_label(TOP_LIMIT + 1)}"):
            break
        limited_lines.append(line)
    limited = "\n".join(limited_lines)
    suffix = "\n(上位5件表示)"
    if len(limited) + len(suffix) > LINE_LIMIT:
        limited = limited[: LINE_LIMIT - len(suffix)]
    return limited + suffix


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, encoding="utf-8")
    test_cases = [
        "TK 渋谷",
        "Java開発",
        "AB/新宿",
        "ZZZZ 存在しない駅",
    ]
    for case in test_cases:
        print(f"\n--- {case} ---")
        print(handle_line_query(case))
