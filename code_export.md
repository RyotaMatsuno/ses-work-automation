# Jobz 繧ｳ繝ｼ繝牙�ｨ菴薙ム繝ｳ繝�

## matching_v2/matching_v2.py

```py
# -*- coding: utf-8 -*-
"""
AI繧ｹ繧ｭ繝ｫ蛻､螳壹ｒ菴ｿ縺｣縺滓｡井ｻｶ ﾃ� 繧ｨ繝ｳ繧ｸ繝九い 繝槭ャ繝√Φ繧ｰ縲�

螳溯｡�:
  python matching_v2/matching_v2.py
"""

import io
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from threading import Lock

import requests
from dotenv import dotenv_values

from skill_judge import judge_skills_batch


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(__file__)
SES_WORK_DIR = os.path.dirname(BASE_DIR)
ENV_PATHS = [
    os.path.join(BASE_DIR, "config", ".env"),
    os.path.join(SES_WORK_DIR, "config", ".env"),
]
PROJECT_DB_ID_DEFAULT = "343450ff-37c0-81e4-934e-f25f90284a3c"
RESULT_PATH = os.path.join(BASE_DIR, "result.json")
SAMPLE_PATH = os.path.join(BASE_DIR, "test_data", "sample.json")
MAX_WORKERS = int(os.environ.get("MATCHING_V2_WORKERS", "4"))


def load_env():
    for env_path in ENV_PATHS:
        if os.path.exists(env_path):
            config = dotenv_values(env_path)
            for key, value in config.items():
                if key not in os.environ and value is not None:
                    os.environ[key] = value


load_env()

API_KEY = os.environ.get("NOTION_API_KEY", "")
ENGINEER_DB_ID = os.environ.get("NOTION_ENGINEER_DB_ID", "")
PROJECT_DB_ID = os.environ.get("NOTION_PROJECT_DB_ID", PROJECT_DB_ID_DEFAULT)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def query_db(db_id, filter_obj=None):
    results = []
    payload = {"page_size": 100}
    if filter_obj:
        payload["filter"] = filter_obj

    while True:
        response = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=HEADERS,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results


def get_multiselect(props, key):
    return [item["name"] for item in props.get(key, {}).get("multi_select", [])]


def get_title(props, key):
    items = props.get(key, {}).get("title", [])
    return items[0]["plain_text"] if items else "�ｼ亥錐蜑阪↑縺暦ｼ�"


def get_number(props, key):
    return props.get(key, {}).get("number")


def get_date(props, key):
    date_value = props.get(key, {}).get("date")
    return date_value["start"] if date_value else None


def get_rich_text(props, key):
    items = props.get(key, {}).get("rich_text", [])
    return items[0]["plain_text"] if items else ""


def judge_with_cache(cache, cache_lock, required_skills, optional_skills, engineers):
    key = (
        tuple(sorted(required_skills)),
        tuple(sorted(optional_skills)),
        tuple(
            sorted(
                (
                    engineer["name"],
                    tuple(sorted(engineer.get("skills", []))),
                )
                for engineer in engineers
            )
        ),
    )
    with cache_lock:
        cached = cache.get(key)
    if cached is not None:
        return cached

    judged = judge_skills_batch(
        list(required_skills),
        list(optional_skills),
        [
            {
                "name": engineer["name"],
                "skills": engineer.get("skills", []),
            }
            for engineer in engineers
        ],
    )
    with cache_lock:
        cache[key] = judged
    return judged


def calculate_score(required_judgement):
    required_results = [item["result"] for item in required_judgement.values()]
    if "ﾃ�" in required_results:
        return 0.0

    triangle_count = required_results.count("笆ｳ")
    if triangle_count == 0:
        return 1.0
    if triangle_count == 1:
        return 0.8
    return 0.65


def needs_check(score, required_judgement):
    required_results = [item["result"] for item in required_judgement.values()]
    return score < 0.7 or "笆ｳ" in required_results


def format_judgement(judgement):
    parts = []
    for skill, item in judgement.items():
        result = item["result"]
        reason = item.get("reason", "")
        if result == "笆ｳ" and reason:
            parts.append(f"{skill}:{result}�ｼ�{reason}�ｼ�")
        else:
            parts.append(f"{skill}:{result}")
    return "  ".join(parts) if parts else "縺ｪ縺�"


def extract_project(page):
    props = page["properties"]
    return {
        "id": page["id"],
        "url": page.get("url"),
        "name": get_title(props, "譯井ｻｶ蜷�"),
        "client": get_rich_text(props, "繧ｯ繝ｩ繧､繧｢繝ｳ繝�") or "荳肴��",
        "required_skills": get_multiselect(props, "蠢�隕√せ繧ｭ繝ｫ"),
        "optional_skills": get_multiselect(props, "蟆壼庄繧ｹ繧ｭ繝ｫ"),
        "price": get_number(props, "蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�"),
        "start_date": get_date(props, "髢句ｧ区律"),
    }


def extract_engineer(page):
    props = page["properties"]
    return {
        "id": page["id"],
        "url": page.get("url"),
        "name": get_title(props, "蜷榊燕"),
        "skills": get_multiselect(props, "繧ｹ繧ｭ繝ｫ"),
        "price": get_number(props, "蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�"),
        "available_date": get_date(props, "遞ｼ蜒榊庄閭ｽ譌･"),
    }


def make_project_result(project, candidates):
    return {
        "project_id": project["id"],
        "project_name": project["name"],
        "project_url": project["url"],
        # 2026-05-25: result.json縺ｧ譯井ｻｶ莠育ｮ励ｒ遒ｺ隱阪〒縺阪ｋ繧医≧budget繧定ｿｽ蜉縲�
        "budget": project["price"],
        "candidates": [
            {
                "engineer_id": candidate["engineer"]["id"],
                "engineer_name": candidate["engineer"]["name"],
                "engineer_url": candidate["engineer"]["url"],
                "score": candidate["score"],
                "needs_check": candidate["needs_check"],
                "required": candidate["required_judgement"],
                "optional": candidate["optional_judgement"],
                "price": candidate["engineer"]["price"],
                "available_date": candidate["engineer"]["available_date"],
            }
            for candidate in candidates
        ],
    }


def evaluate_candidate(project, engineer, judgement):
    # 2026-05-25: 譯井ｻｶ莠育ｮ励ｒ螟ｧ蟷�縺ｫ雜�縺医ｋ蜊倅ｾ｡縺ｮ蛟呵｣懊�ｯ繧ｹ繧ｭ繝ｫ蛻､螳壼燕縺ｫ髯､螟悶�
    if (
        engineer["price"] is not None
        and project["price"] is not None
        and engineer["price"] > project["price"] + 5
    ):
        return None

    required_judgement = {
        skill: judgement[skill] for skill in project["required_skills"]
    }
    optional_judgement = {
        skill: judgement[skill] for skill in project["optional_skills"]
    }
    score = calculate_score(required_judgement)

    if score == 0.0:
        return None

    return {
        "engineer": engineer,
        "score": score,
        "needs_check": needs_check(score, required_judgement),
        "required_judgement": required_judgement,
        "optional_judgement": optional_judgement,
    }


def print_summary(projects_results):
    print("=" * 65)
    print("AI繝槭ャ繝√Φ繧ｰ邨先棡")
    print("=" * 65)

    for project_result in projects_results:
        project = project_result["project"]
        candidates = project_result["candidates"]
        print(f"譯井ｻｶ: {project['name']}")
        print(f"  繧ｯ繝ｩ繧､繧｢繝ｳ繝�: {project['client']}")
        print(f"  蠢�鬆�: {', '.join(project['required_skills']) or '縺ｪ縺�'}")
        print(f"  蟆壼庄: {', '.join(project['optional_skills']) or '縺ｪ縺�'}")

        if not candidates:
            print("  竊� 蛟呵｣懊↑縺�")
            print()
            continue

        for index, candidate in enumerate(candidates, start=1):
            engineer = candidate["engineer"]
            print(f"  蛟呵｣悳index}: {engineer['name']}�ｼ医せ繧ｳ繧｢: {candidate['score']:.2f}�ｼ�")
            print(f"    蠢�鬆�: {format_judgement(candidate['required_judgement'])}")
            print(f"    蟆壼庄: {format_judgement(candidate['optional_judgement'])}")
            price = f"{engineer['price']}荳�" if engineer["price"] else "譛ｪ險ｭ螳�"
            available_date = engineer["available_date"] or "譛ｪ險ｭ螳�"
            print(f"    蜊倅ｾ｡: {price} / 遞ｼ蜒�: {available_date}")
            if candidate["needs_check"]:
                print("    竊� 隕∫｢ｺ隱� 笞�ｸ擾ｼ域收驥弱↓遒ｺ隱阪ヵ繝ｩ繧ｰ�ｼ�")
            else:
                print("    竊� 謠先｡域耳螂ｨ 笨�")
        print()


def validate_env():
    missing = [
        key for key in ["NOTION_API_KEY", "NOTION_ENGINEER_DB_ID", "ANTHROPIC_API_KEY"]
        if not os.environ.get(key)
    ]
    if missing:
        raise RuntimeError(f"蠢�隕√↑迺ｰ蠅�螟画焚縺梧悴險ｭ螳壹〒縺�: {', '.join(missing)}")


def validate_sample_env():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("蠢�隕√↑迺ｰ蠅�螟画焚縺梧悴險ｭ螳壹〒縺�: ANTHROPIC_API_KEY")


def load_sample_data():
    with open(SAMPLE_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    projects = []
    for project in data.get("projects", []):
        projects.append({
            "id": project["id"],
            "url": project.get("url"),
            "name": project["name"],
            "client": project.get("client", "繧ｵ繝ｳ繝励Ν"),
            "required_skills": project.get("required_skills", []),
            "optional_skills": project.get("optional_skills", []),
            "price": project.get("price"),
            "start_date": project.get("start_date"),
        })

    engineers = []
    for engineer in data.get("engineers", []):
        engineers.append({
            "id": engineer["id"],
            "url": engineer.get("url"),
            "name": engineer["name"],
            "skills": engineer.get("skills", []),
            "price": engineer.get("price"),
            "available_date": engineer.get("available_date"),
        })

    return projects, engineers


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample",
        action="store_true",
        help="test_data/sample.json繧剃ｽｿ縺�縲¨otion API繧貞他縺ｰ縺壹↓螳溯｡後☆繧�",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.sample:
        validate_sample_env()
        projects, engineers = load_sample_data()
    else:
        validate_env()
        projects = [
            extract_project(page)
            for page in query_db(PROJECT_DB_ID, {
                "property": "繧ｹ繝�繝ｼ繧ｿ繧ｹ",
                "select": {"equals": "蜍滄寔荳ｭ"},
            })
        ]
        engineers = [
            extract_engineer(page)
            for page in query_db(ENGINEER_DB_ID, {
                "property": "遞ｼ蜒咲憾豕�",
                "select": {"equals": "遞ｼ蜒榊庄閭ｽ"},
            })
        ]

    print(f"蜍滄寔荳ｭ譯井ｻｶ: {len(projects)}莉ｶ / 遞ｼ蜒榊庄閭ｽ繧ｨ繝ｳ繧ｸ繝九い: {len(engineers)}蜷�")

    cache = {}
    cache_lock = Lock()
    projects_results = []
    output_projects = []

    for project in projects:
        candidates = []
        if not project["required_skills"] and not project["optional_skills"]:
            print(f"蛻､螳壹せ繧ｭ繝�繝�: {project['name']}�ｼ医せ繧ｭ繝ｫ隕∽ｻｶ縺ｪ縺暦ｼ�", flush=True)
            projects_results.append({
                "project": project,
                "candidates": candidates,
            })
            output_projects.append(make_project_result(project, candidates))
            continue

        print(f"蛻､螳壻ｸｭ: {project['name']}�ｼ�{len(engineers)}蜷搾ｼ�", flush=True)

        batch_judgement = judge_with_cache(
            cache,
            cache_lock,
            project["required_skills"],
            project["optional_skills"],
            engineers,
        )
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for engineer in engineers:
                judgement = batch_judgement.get(engineer["name"], {})
                futures.append(executor.submit(
                    evaluate_candidate,
                    project,
                    engineer,
                    judgement,
                ))
            for future in as_completed(futures):
                candidate = future.result()
                if candidate is None:
                    continue
                candidates.append(candidate)

        candidates.sort(key=lambda item: item["score"], reverse=True)
        projects_results.append({
            "project": project,
            "candidates": candidates,
        })
        output_projects.append(make_project_result(project, candidates))

    with open(RESULT_PATH, "w", encoding="utf-8") as file:
        json.dump(output_projects, file, ensure_ascii=False, indent=2)

    # 2026-05-25: 蟆壼庄繧ｹ繧ｭ繝ｫ遨ｺ蝠城｡後�ｮ蜴溷屏隱ｿ譟ｻ逕ｨ縺ｫ莉ｶ謨ｰ繧貞�ｺ蜉帙�
    optional_skill_projects = sum(1 for project in projects if project["optional_skills"])
    print(f"蟆壼庄繧ｹ繧ｭ繝ｫ縺ゅｊ: {optional_skill_projects}/{len(projects)}莉ｶ")

    print_summary(projects_results)
    print(f"result.json 逕滓��: {RESULT_PATH}")


if __name__ == "__main__":
    main()

```

## matching_v2/notify_line.py

```py
# -*- coding: utf-8 -*-
"""
諡�蠖楢�蛻･LINE騾夂衍繧ｹ繧ｯ繝ｪ繝励ヨ縲�

螳溯｡�:
  python matching_v2/notify_line.py --dry-run
  python matching_v2/notify_line.py
"""

import argparse
import io
import json
import os
import sys

import requests

try:
    from dotenv import dotenv_values
except ImportError:
    dotenv_values = None


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(__file__)
SES_WORK_DIR = os.path.dirname(BASE_DIR)
ENV_PATHS = [
    os.path.join(BASE_DIR, "config", ".env"),
    os.path.join(SES_WORK_DIR, "config", ".env"),
]
RESULT_PATH = os.path.join(BASE_DIR, "result.json")
NOTION_VERSION = "2022-06-28"
DEFAULT_ASSIGNEE = "譚ｾ驥�"
OKAMOTO = "蟯｡譛ｬ"


def main():
    args = parse_args()
    load_env()

    notion_headers = build_notion_headers()
    line_accounts = None if args.dry_run else build_line_accounts()
    results = load_result(args.result_path)

    assignee_cache = {}
    info_cache = {}
    project_notify_count = 0
    notification_count = 0
    skipped_count = 0
    notification_batches = []

    for item in results:
        candidates = item.get("candidates") or []
        if not candidates:
            skipped_count += 1
            continue

        project_id = get_project_id(item)
        project_info = get_page_info_cached(project_id, notion_headers, info_cache, "project")
        if not project_info.get("name"):
            project_info["name"] = get_project_name(item)
        if project_info.get("price") is None:
            project_info["price"] = get_project_price(item)
        if not project_info.get("start_date"):
            project_info["start_date"] = get_project_start_date(item)
        project_assignee = get_assignee_cached(project_id, notion_headers, assignee_cache)
        candidate_infos = []

        for candidate in candidates:
            engineer_id = get_engineer_id(candidate)
            engineer_assignee = get_assignee_cached(engineer_id, notion_headers, assignee_cache)
            engineer_info = get_page_info_cached(engineer_id, notion_headers, info_cache, "engineer")
            if not engineer_info.get("name"):
                engineer_info["name"] = get_engineer_name(candidate)
            if engineer_info.get("price") is None:
                engineer_info["price"] = candidate.get("price")
            if not engineer_info.get("available_date"):
                engineer_info["available_date"] = candidate.get("available_date")
            candidate_infos.append({
                "candidate": candidate,
                "engineer_info": engineer_info,
                "engineer_assignee": engineer_assignee,
            })

        notifications = build_notifications(
            project_info=project_info,
            project_assignee=project_assignee,
            candidate_infos=candidate_infos,
        )

        notification_batches.append((is_line_source(project_info.get("input_source")), notifications))
        project_notify_count += 1

    notification_batches.sort(key=lambda batch: 0 if batch[0] else 1)
    for _, notifications in notification_batches:
        for assignee, text in notifications:
            if args.dry_run:
                print_dry_run(assignee, text)
            else:
                account = line_accounts[assignee]
                status_code, response_text = push_message(
                    account["channel_token"],
                    account["user_id"],
                    text,
                )
                print(f"[sent] to={assignee} status={status_code} response={response_text}")
            notification_count += 1

    mode = "dry-run" if args.dry_run else "send"
    print(
        f"[done] mode={mode} projects={project_notify_count} "
        f"notifications={notification_count} skipped_empty_projects={skipped_count}"
    )


def load_env():
    for env_path in ENV_PATHS:
        if not os.path.exists(env_path):
            continue

        if dotenv_values is not None:
            config = dotenv_values(env_path)
        else:
            config = read_env_file(env_path)

        for key, value in config.items():
            if key not in os.environ and value is not None:
                os.environ[key] = value


def read_env_file(env_path):
    config = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip().strip('"').strip("'")
    return config


def push_message(channel_token: str, user_id: str, text: str):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {channel_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}],
    }
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    return response.status_code, response.text


def get_assignee(page_id: str, headers: dict) -> str:
    """Notion繝壹�ｼ繧ｸ縺ｮID縺九ｉ諡�蠖楢�繧貞叙蠕励よ悴險ｭ螳壹�ｻ蜈ｱ騾壹�ｯ繝�繝輔か繝ｫ繝�'譚ｾ驥�'繧定ｿ斐☆縲�"""
    if not page_id:
        return DEFAULT_ASSIGNEE
    if os.environ.get("SKIP_NOTION_FETCH") == "1":
        return DEFAULT_ASSIGNEE

    response = requests.get(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    props = response.json().get("properties", {})
    select_value = props.get("諡�蠖楢�", {}).get("select")
    name = select_value["name"] if select_value else None
    if name == OKAMOTO:
        return OKAMOTO
    return DEFAULT_ASSIGNEE


def load_result(result_path: str):
    with open(result_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("result.json must be a list")
    return data


def get_assignee_cached(page_id, headers, cache):
    if page_id not in cache:
        cache[page_id] = get_assignee(page_id, headers)
    return cache[page_id]


def get_page_info_cached(page_id, headers, cache, page_type):
    key = (page_type, page_id)
    if key not in cache:
        cache[key] = get_page_info(page_id, headers, page_type)
    return dict(cache[key])


def get_page_info(page_id, headers, page_type):
    if not page_id:
        return empty_page_info(page_type)
    if os.environ.get("SKIP_NOTION_FETCH") == "1":
        return empty_page_info(page_type)

    response = requests.get(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    props = response.json().get("properties", {})

    if page_type == "project":
        return {
            "name": get_title_property(props, "譯井ｻｶ蜷�"),
            "detail": get_first_text_property(props, ["讌ｭ蜍吝��螳ｹ", "譯井ｻｶ隧ｳ邏ｰ", "隧ｳ邏ｰ", "讎りｦ�", "蜀�螳ｹ"]),
            "required_skills": get_first_multiselect_property(props, ["蠢�鬆医せ繧ｭ繝ｫ", "蠢�隕√せ繧ｭ繝ｫ"]),
            "optional_skills": get_multiselect_property(props, "蟆壼庄繧ｹ繧ｭ繝ｫ"),
            "price": get_number_property(props, "蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�"),
            "start_date": get_date_property(props, "髢句ｧ区律"),
            "input_source": get_text_property(props, "蜈･蜉帛��"),
            "affiliation": get_text_property(props, "謇螻樔ｼ夂､ｾ蜷�"),
        }

    if page_type == "engineer":
        return {
            "name": get_title_property(props, "蜷榊燕"),
            "skills": get_multiselect_property(props, "繧ｹ繧ｭ繝ｫ"),
            "price": get_number_property(props, "蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�"),
            "available_date": get_date_property(props, "遞ｼ蜒榊庄閭ｽ譌･"),
            "input_source": get_text_property(props, "蜈･蜉帛��"),
            "affiliation": get_text_property(props, "謇螻樔ｼ夂､ｾ蜷�"),
        }

    raise ValueError(f"unsupported page_type: {page_type}")


def empty_page_info(page_type):
    if page_type == "project":
        return {
            "name": "",
            "detail": "",
            "required_skills": [],
            "optional_skills": [],
            "price": None,
            "start_date": None,
            "input_source": "",
            "affiliation": "",
        }
    return {
        "name": "",
        "skills": [],
        "price": None,
        "available_date": None,
        "input_source": "",
        "affiliation": "",
    }


def build_notifications(project_info, project_assignee, candidate_infos):
    assignees = {project_assignee}
    for item in candidate_infos:
        assignees.add(item["engineer_assignee"])

    message = build_project_message(project_info, candidate_infos)
    return [(assignee, message) for assignee in sorted(assignees)]


def build_project_message(project_info, candidate_infos):
    input_source = project_info.get("input_source")
    line_prefix = "  笞｡LINE譯井ｻｶ" if is_line_source(input_source) else ""
    lines = [
        "縲舌�槭ャ繝√Φ繧ｰ邨先棡縲�",
        f"譯井ｻｶ: {format_value(project_info.get('name'))}{line_prefix}",
    ]
    if project_info.get("affiliation"):
        lines.append(f"謇螻�: {project_info.get('affiliation')}")
    lines.extend([
        f"蜈･蜉帛��: {format_value(input_source)}",
        f"讌ｭ蜍吝��螳ｹ: {format_value(project_info.get('detail'))}",
        f"蠢�鬆�: {format_list(project_info.get('required_skills'))}",
        f"蟆壼庄: {format_list(project_info.get('optional_skills'))}",
        f"蜊倅ｾ｡: {format_price(project_info.get('price'))}",
        f"遞ｼ蜒�: {format_value(project_info.get('start_date'))}",
        "笏笏笏笏笏笏笏笏笏笏笏笏笏笏",
    ])

    for item in candidate_infos:
        candidate = item["candidate"]
        engineer_info = item["engineer_info"]
        # 2026-05-25: needs_check蛟呵｣懊′騾夂衍荳翫〒蛻､蛻･縺ｧ縺阪ｋ繧医≧隴ｦ蜻翫ｒ霑ｽ險倥�
        needs_check_warning = " 笞�ｸ剰ｦ∫｢ｺ隱�" if candidate.get("needs_check") is True else ""
        lines.extend([
            f"笆ｶ {format_value(engineer_info.get('name'))}�ｼ医せ繧ｳ繧｢: {format_score(candidate.get('score'))}�ｼ閲needs_check_warning}",
        ])
        if engineer_info.get("affiliation"):
            lines.append(f"  謇螻�: {engineer_info.get('affiliation')}")
        lines.extend([
            f"  蜈･蜉帛��: {format_value(engineer_info.get('input_source'))}",
            (
                f"  蜊倅ｾ｡: {format_price(engineer_info.get('price'))} / "
                f"遞ｼ蜒�: {format_value(engineer_info.get('available_date'))}"
            ),
            f"  繧ｹ繧ｭ繝ｫ: {format_list(engineer_info.get('skills'))}",
            f"  蠢�鬆亥愛螳�: {format_judgement(get_required_judgement(candidate))}",
            f"  蟆壼庄蛻､螳�: {format_judgement(get_optional_judgement(candidate))}",
            "",
        ])

    lines.extend([
        "笏笏笏笏笏笏笏笏笏笏笏笏笏笏",
        "諢丞髄遒ｺ隱阪ｒ縺企｡倥＞縺励∪縺吶�",
    ])
    return "\n".join(lines)


def is_line_source(input_source):
    return str(input_source or "").endswith("LINE")


def parse_args():
    parser = argparse.ArgumentParser(description="result.json繧定ｪｭ縺ｿ縲∵球蠖楢�蛻･縺ｫLINE Push騾夂衍縺励∪縺吶�")
    parser.add_argument("--dry-run", action="store_true", help="LINE騾∽ｿ｡縺帙★騾夂衍蜀�螳ｹ繧偵さ繝ｳ繧ｽ繝ｼ繝ｫ蜃ｺ蜉帙＠縺ｾ縺吶�")
    parser.add_argument("--result-path", default=RESULT_PATH, help="隱ｭ縺ｿ霎ｼ繧result.json縺ｮ繝代せ縲�")
    return parser.parse_args()


def get_project_id(item):
    project = item.get("project") or {}
    return project.get("id") or item.get("project_id") or ""


def get_project_name(item):
    project = item.get("project") or {}
    return project.get("name") or item.get("project_name") or "�ｼ域｡井ｻｶ蜷阪↑縺暦ｼ�"


def get_project_price(item):
    project = item.get("project") or {}
    return project.get("price") or item.get("price")


def get_project_start_date(item):
    project = item.get("project") or {}
    return project.get("start_date") or item.get("start_date")


def get_engineer_id(candidate):
    return candidate.get("id") or candidate.get("engineer_id") or ""


def get_engineer_name(candidate):
    return candidate.get("name") or candidate.get("engineer_name") or "�ｼ医お繝ｳ繧ｸ繝九い蜷阪↑縺暦ｼ�"


def get_required_judgement(candidate):
    return candidate.get("required_judgement") or candidate.get("required") or {}


def get_optional_judgement(candidate):
    return candidate.get("optional_judgement") or candidate.get("optional") or {}


def get_title_property(props, key):
    items = props.get(key, {}).get("title", [])
    return items[0]["plain_text"] if items else ""


def get_text_property(props, key):
    prop = props.get(key, {})
    if prop.get("type") == "rich_text":
        return "".join(item.get("plain_text", "") for item in prop.get("rich_text", []))
    if prop.get("type") == "title":
        return "".join(item.get("plain_text", "") for item in prop.get("title", []))
    if prop.get("type") == "select":
        select_value = prop.get("select")
        return select_value.get("name", "") if select_value else ""
    if prop.get("type") == "multi_select":
        return format_list(item.get("name", "") for item in prop.get("multi_select", []))
    return ""


def get_first_text_property(props, keys):
    for key in keys:
        value = get_text_property(props, key)
        if value:
            return value
    return ""


def get_multiselect_property(props, key):
    return [item["name"] for item in props.get(key, {}).get("multi_select", [])]


def get_first_multiselect_property(props, keys):
    for key in keys:
        value = get_multiselect_property(props, key)
        if value:
            return value
    return []


def get_number_property(props, key):
    return props.get(key, {}).get("number")


def get_date_property(props, key):
    date_value = props.get(key, {}).get("date")
    return date_value["start"] if date_value else None


def format_judgement(judgement):
    if not judgement:
        return "縺ｪ縺�"

    parts = []
    for skill, value in judgement.items():
        result = value.get("result") if isinstance(value, dict) else value
        parts.append(f"{skill}:{result}")
    return " / ".join(parts)


def format_price(price):
    if price is None or price == "":
        return "譛ｪ險ｭ螳�"
    return f"{price}荳�蜀�"


def format_score(score):
    if score is None:
        return "譛ｪ險ｭ螳�"
    if isinstance(score, float):
        return f"{score:.2f}".rstrip("0").rstrip(".")
    return str(score)


def format_list(values):
    items = [str(value) for value in (values or []) if value not in (None, "")]
    return ", ".join(items) if items else "縺ｪ縺�"


def format_value(value):
    return str(value) if value not in (None, "") else "譛ｪ險ｭ螳�"


def build_notion_headers():
    api_key = os.environ.get("NOTION_API_KEY", "")
    if not api_key:
        raise RuntimeError("NOTION_API_KEY is not set")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def build_line_accounts():
    accounts = {
        DEFAULT_ASSIGNEE: {
            "channel_token": os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""),
            "user_id": os.environ.get("MATSUNO_LINE_USER_ID", ""),
        },
        OKAMOTO: {
            "channel_token": os.environ.get("OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN")
            or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""),
            "user_id": os.environ.get("OKAMOTO_LINE_USER_ID", ""),
        },
    }

    missing = []
    for assignee, account in accounts.items():
        if not account["channel_token"]:
            missing.append(f"{assignee}: channel token")
        if not account["user_id"]:
            missing.append(f"{assignee}: user id")
    if missing:
        raise RuntimeError("LINE environment variables are not set: " + ", ".join(missing))
    return accounts


def print_dry_run(assignee, text):
    print("=" * 60)
    print(f"[dry-run] to={assignee}")
    print(text)


if __name__ == "__main__":
    main()

```

## line_webhook/webhook_server.py

```py
"""

LINE Webhook Server v13

- 繧ｹ繧ｭ繝ｫ繧ｷ繝ｼ繝�PDF/逕ｻ蜒上ｒLINE縺九ｉ蜿嶺ｿ｡縺励※skill_reader_api�ｼ�8766�ｼ峨〒蜃ｦ逅�

"""



import os, hmac, hashlib, base64, json, re, traceback, threading, time

from datetime import date, datetime

from flask import Flask, request, abort

import requests

from dotenv import dotenv_values, set_key
from remote_command_handler import execute_remote, execute_bg, get_log, get_health
try:
    from matching_logic import deduplicate_projects, build_reverse_match_message_v2
    MATCHING_LOGIC_AVAILABLE = True
except ImportError:
    MATCHING_LOGIC_AVAILABLE = False
    def deduplicate_projects(p): return p



ENV_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')

if os.path.exists(ENV_PATH):

    config = dotenv_values(ENV_PATH)

    for key, value in config.items():

        if key not in os.environ:

            os.environ[key] = value



MATSUNO_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')

MATSUNO_CHANNEL_TOKEN  = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')

MATSUNO_USER_ID        = os.environ.get('MATSUNO_LINE_USER_ID') or '***MASKED***'

OKAMOTO_CHANNEL_SECRET = os.environ.get('LINE_OKAMOTO_CHANNEL_SECRET') or os.environ.get('OKAMOTO_LINE_CHANNEL_SECRET', '')

OKAMOTO_CHANNEL_TOKEN  = os.environ.get('LINE_OKAMOTO_CHANNEL_TOKEN') or os.environ.get('OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN', '')

OKAMOTO_USER_ID        = os.environ.get('OKAMOTO_LINE_USER_ID') or '***MASKED***'

NOTION_API_KEY         = os.environ.get('NOTION_API_KEY', '')

NOTION_ENGINEER_DB_ID  = os.environ.get('NOTION_ENGINEER_DB_ID', '')

NOTION_PROJECT_DB_ID   = os.environ.get('NOTION_PROJECT_DB_ID', '')

ANTHROPIC_API_KEY      = os.environ.get('ANTHROPIC_API_KEY', '')



app = Flask(__name__)

NOTION_HEADERS = {

    "Authorization": f"Bearer {NOTION_API_KEY}",

    "Content-Type": "application/json",

    "Notion-Version": "2022-06-28"

}

DB_PROPERTY_CACHE = {}


def get_line_source_label(user_id: str) -> str:
    if user_id == MATSUNO_USER_ID:
        return "譚ｾ驥鮫INE"
    if user_id == OKAMOTO_USER_ID:
        return "蟯｡譛ｬLINE"
    return "譚ｾ驥鮫INE"

VALID_SKILLS = [
    "Java","Python","PHP","JavaScript","TypeScript","C#","C++","C","Go","Ruby",
    "Swift","Kotlin","R","COBOL","VB.NET","VBA","Scala","Rust","Perl","Bash",
    "React","Vue.js","Angular","Next.js","Nuxt.js","HTML","CSS","jQuery",
    "Node.js","Spring","Spring Boot","Django","Flask","Laravel","Rails",".NET",
    "Express","FastAPI",
    "AWS","GCP","Azure","Docker","Kubernetes","Terraform","Ansible","Linux",
    "Windows Server","VMware","OpenStack","Nginx","Apache",
    "MySQL","PostgreSQL","Oracle","SQL Server","MongoDB","Redis","Elasticsearch",
    "DynamoDB","Cassandra","SQLite",
    "Jenkins","GitLab","GitHub Actions","CircleCI","Git","Jira","Confluence",
    "Tableau","PowerBI","Spark","Hadoop","TensorFlow","PyTorch","scikit-learn",
    "Salesforce","SAP","ServiceNow","SharePoint","Power Apps","Power Automate",
    "CCNA","CCNP","Cisco","Fortinet","Zabbix","Prometheus",
    "FPGA","PLC","Unity","Android Studio","Xcode"
]



SHEET_URL_PATTERN = re.compile(r'https://docs\.google\.com/spreadsheets/[^\s]+')

EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

KANTO_CHUBU_PREFECTURES = {
    "譚ｱ莠ｬ驛ｽ", "逾槫･亥ｷ晉恁", "蝓ｼ邇臥恁", "蜊�闡臥恁", "闌ｨ蝓守恁", "譬�譛ｨ逵�", "鄒､鬥ｬ逵�",
    "諢帷衍逵�", "蟯宣�懃恁", "荳蛾㍾逵�", "髱吝ｲ｡逵�", "髟ｷ驥守恁", "蟇悟ｱｱ逵�", "遏ｳ蟾晉恁",
    "遖丈ｺ慕恁", "螻ｱ譴ｨ逵�", "譁ｰ貎溽恁",
}

ALL_PREFECTURES = [
    "蛹玲ｵｷ驕�", "髱呈｣ｮ逵�", "蟯ｩ謇狗恁", "螳ｮ蝓守恁", "遘狗伐逵�", "螻ｱ蠖｢逵�", "遖丞ｳｶ逵�",
    "闌ｨ蝓守恁", "譬�譛ｨ逵�", "鄒､鬥ｬ逵�", "蝓ｼ邇臥恁", "蜊�闡臥恁", "譚ｱ莠ｬ驛ｽ", "逾槫･亥ｷ晉恁",
    "譁ｰ貎溽恁", "蟇悟ｱｱ逵�", "遏ｳ蟾晉恁", "遖丈ｺ慕恁", "螻ｱ譴ｨ逵�", "髟ｷ驥守恁", "蟯宣�懃恁",
    "髱吝ｲ｡逵�", "諢帷衍逵�", "荳蛾㍾逵�", "貊玖ｳ逵�", "莠ｬ驛ｽ蠎�", "螟ｧ髦ｪ蠎�", "蜈ｵ蠎ｫ逵�",
    "螂郁憶逵�", "蜥梧ｭ悟ｱｱ逵�", "魑･蜿也恁", "蟲ｶ譬ｹ逵�", "蟯｡螻ｱ逵�", "蠎�蟲ｶ逵�", "螻ｱ蜿｣逵�",
    "蠕ｳ蟲ｶ逵�", "鬥吝ｷ晉恁", "諢帛ｪ帷恁", "鬮倡衍逵�", "遖丞ｲ｡逵�", "菴占ｳ逵�", "髟ｷ蟠守恁",
    "辭頑悽逵�", "螟ｧ蛻�逵�", "螳ｮ蟠守恁", "鮖ｿ蜈仙ｳｶ逵�", "豐也ｸ�逵�",
]

PREFECTURE_ALIASES = {
    pref.replace("驛ｽ", "").replace("蠎�", "").replace("逵�", ""): pref
    for pref in ALL_PREFECTURES
    if pref not in ("蛹玲ｵｷ驕�", "莠ｬ驛ｽ蠎�")
}
PREFECTURE_ALIASES["蛹玲ｵｷ驕�"] = "蛹玲ｵｷ驕�"

ENGINEER_NAME_NOT_FOUND_REPLY = "蜷榊燕縺悟叙蠕励〒縺阪∪縺帙ｓ縺ｧ縺励◆縲ゅ梧ｰ丞錐: 縲�縲�縲阪�ｮ蠖｢蠑上〒蜀埼√＠縺ｦ縺上□縺輔＞縲�"
AREA_OUT_OF_SCOPE_REPLY = "蟇ｾ蠢懊お繝ｪ繧｢螟悶�ｮ縺溘ａ逋ｻ骭ｲ繧偵せ繧ｭ繝�繝励＠縺ｾ縺励◆�ｼ磯未譚ｱ繝ｻ荳ｭ驛ｨ縺ｮ縺ｿ蟇ｾ蠢懶ｼ�"



PENDING_PROPOSALS = {}

# 繧ｹ繧ｭ繝ｫ繧ｷ繝ｼ繝郁ｧ｣譫千ｵ先棡縺ｮ荳譎ゆｿ晏ｭ� key: sender+"_skill" 竊� iko_mail text

PENDING_SKILL_MAIL = {}





def verify_signature(body, signature, secret):

    h = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).digest()

    return hmac.compare_digest(base64.b64encode(h).decode('utf-8'), signature)





def call_claude(system, user_msg, max_tokens=2000):

    res = requests.post(

        "https://api.anthropic.com/v1/messages",

        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},

        json={"model": "claude-haiku-4-5-20251001", "max_tokens": max_tokens,

              "system": system, "messages": [{"role": "user", "content": user_msg}]},

        timeout=60

    )

    if res.status_code == 200:

        return res.json()["content"][0]["text"]

    print(f"Claude API error: {res.status_code} {res.text[:100]}")

    return ""





def normalize_price(price):

    if price is None or price == 0:

        return price

    if price >= 1000:

        price = round(price / 10000)

    return price





def classify_message(text):
    system = """You are an SES message classifier for a Japanese IT staffing company.
Reply JSON only. No markdown. No explanation.

Rules:
- price: man-yen integer. "65man"->65, "45-50man"->47, "650000yen"->65
- skills: normalize to English. C-plus-plus->C++, TypeScript->TypeScript
- location: extract city/ward. full-remote->full-remote
- available_date: YYYY-MM-DD or "sokujitsu"
- experience_years: integer estimate
- affiliation: engineer's affiliation company name
- contact_name: affiliation-side contact person name
- contact_email: affiliation-side contact email address
- If forwarded message, extract only the embedded job/person info

Output ONE of these JSON shapes:

Single engineer: {"type":"engineer","name":"","skills":[],"price":0,"available_date":"","experience_years":0,"location":"","note":"","affiliation":"","contact_name":"","contact_email":""}

Multiple engineers: {"type":"engineers","engineers":[{"type":"engineer","name":"","skills":[],"price":0,"available_date":"","experience_years":0,"location":"","note":"","affiliation":"","contact_name":"","contact_email":""}]}

Single job: {"type":"project","name":"","required_skills":[],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"unknown","period":"","interview_count":0,"note":""}

Multiple jobs: {"type":"projects","projects":[...]}

Other: {"type":"other","note":""}

Examples:
Input: "Java/Spring 5nen, Tanaka, 65man, sokujitsu, Tokyo"
Output: {"type":"engineer","name":"Tanaka","skills":["Java","Spring Boot"],"price":65,"available_date":"sokujitsu","experience_years":5,"location":"Tokyo","note":"","affiliation":"","contact_name":"","contact_email":""}

Input: "Kyuubo React TypeScript hissu, Next.js shoko, 55-60man, Shibuya shu3remote, 7gatsu"
Output: {"type":"project","name":"React/TypeScript case","required_skills":["React","TypeScript"],"optional_skills":["Next.js"],"price":57,"start_date":"2026-07-01","location":"Shibuya","remote":"shu3","period":"long","interview_count":1,"note":"kyuubo"}
"""
    result = call_claude(system, text, max_tokens=2000)

    try:

        result_obj = json.loads(re.sub(r'```json|```', '', result).strip())

        if not isinstance(result_obj, dict):

            return {"type": "other", "note": text[:300]}

        return result_obj

    except Exception as e:

        print(f"[classify_message] parse error: {e} / raw: {result[:100]}")

        return {"type": "other", "note": text[:300]}





def classify_sheet_content(text):

    system = '''Classify this spreadsheet content. Reply JSON only.

{"content_type": "engineer"} or {"content_type": "project"}'''

    result = call_claude(system, text[:2000], max_tokens=100)

    try:

        return json.loads(re.sub(r'```json|```', '', result).strip()).get("content_type", "engineer")

    except Exception:

        return "engineer"





def fetch_sheet_text(url):

    try:

        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mail_attachment_importer'))

        from sheet_fetcher import fetch_sheet_text as _fetch

        return _fetch(url)

    except Exception as e:

        return {"status": "error", "error": str(e)}





def extract_engineers_from_text(text):

    try:

        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mail_attachment_importer'))

        from ai_extractor import extract_engineers

        return extract_engineers(text, "sheet_from_line")

    except Exception as e:

        return []





def extract_projects_from_text(text):

    try:

        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mail_attachment_importer'))

        from ai_extractor import extract_projects

        return extract_projects(text, "sheet_from_line")

    except Exception as e:

        return []





def run_matching(project, engineers):
    system = """SES matching AI. Reply JSON only. No markdown.

Business Rules:
- gross_profit = project_price - engineer_price (both in man-yen)
- gross < 5: NG reason "grori-fusoku"
- All required_skills must match: if any missing -> required_ok=false
- score 0-100: required match 60pts + optional match rate 20pts + gross quality 20pts (7man=100pct,5man=50pct)
- proposal_draft: formal Japanese business email. Use templates.
- FORBIDDEN in proposal: beshsa/toshsa -> remove, sokusenjryoku -> "match-do-takai-jinzai", oshiete-kudasai -> "gokyujyu-kudasai", jyuusoku -> "subete mitashite-ori"
- proposal format: list top candidates with single-line summary each

Output:
{"candidates":[{
  "name":"",
  "price":0,
  "available_date":"",
  "score":0,
  "gross_profit":0,
  "required_match":{"Java":true},
  "optional_match":{"Docker":true},
  "required_ok":true,
  "ng_reasons":[],
  "summary":""
}],"proposal_draft":""}
"""
    result = call_claude(system, json.dumps({"project": project, "engineers": engineers}, ensure_ascii=False), max_tokens=3000)
    try:
        result_obj = json.loads(re.sub(r'```json|```', '', result).strip())
        if not isinstance(result_obj, dict):
            return {"candidates": [], "proposal_draft": ""}
        return result_obj
    except Exception as e:
        print(f"[run_matching] parse error: {e}")
        return {"candidates": [], "proposal_draft": ""}


def run_reverse_matching(engineer, projects):
    system = """SES reverse matching AI. Reply JSON only. No markdown.

Rules:
- gross_profit = project_price - engineer_price
- ONLY include projects where gross_profit >= 5
- score 0-100: skill match 70pts + gross quality 30pts
- Sort by score desc, return top matches
- If engineer price unknown, estimate from experience

Output:
{"matches":[{
  "project_name":"",
  "project_price":0,
  "score":0,
  "gross_profit":0,
  "required_match":{"Java":true},
  "optional_match":{},
  "note":""
}]}
"""
    result = call_claude(system, json.dumps({"engineer": engineer, "projects": projects}, ensure_ascii=False), max_tokens=2000)
    try:
        result_obj = json.loads(re.sub(r'```json|```', '', result).strip())
        if not isinstance(result_obj, dict):
            return {"matches": []}
        return result_obj
    except Exception as e:
        print(f"[run_reverse_matching] parse error: {e}")
        return {"matches": []}


def evaluate_candidate(candidate, project_price):
    ng_reasons = list(candidate.get("ng_reasons", []))

    required_ok = candidate.get("required_ok", None)
    if required_ok is False:
        required_match = candidate.get("required_match", {})
        missing = [k for k, v in required_match.items() if not v]
        if missing:
            label = f"hissu-NG: {', '.join(missing)}"
            if label not in ng_reasons:
                ng_reasons.append(label)

    cp = normalize_price(candidate.get("price", 0)) or 0
    pp = normalize_price(project_price) or 0
    gross = candidate.get("gross_profit", 0)
    if gross == 0 and cp > 0 and pp > 0:
        gross = pp - cp
    if cp == 0:
        ng_reasons.append("tanka-mishettei")
    elif gross > 0 and gross < 5:
        ng_reasons.append(f"grori {gross}man (min 5man)")

    is_ok = len(ng_reasons) == 0

    required_match = candidate.get("required_match", {})
    req_str = " ".join(f"{'O' if v else 'X'}{k}" for k, v in required_match.items()) if required_match else ""
    opt_match = candidate.get("optional_match", {})
    opt_str = " ".join(f"{'O' if v else 'D'}{k}" for k, v in opt_match.items()) if opt_match else ""

    detail_parts = []
    if req_str: detail_parts.append(f"hissu: {req_str}")
    if opt_str: detail_parts.append(f"shoko: {opt_str}")

    return is_ok, ng_reasons, " / ".join(detail_parts)


def build_matching_message(proj_name, ok_candidates, ng_candidates, proposal_draft):

    msg = f"投 譯井ｻｶ縲施proj_name}縲冗匳骭ｲ繝ｻ繝槭ャ繝√Φ繧ｰ螳御ｺ�\n\n"



    if ok_candidates:

        msg += f"笨� OK蛟呵｣�: {len(ok_candidates)}蜷構n"

        for i, (c, detail) in enumerate(ok_candidates, 1):

            price = normalize_price(c.get("price", 0)) or 0

            msg += f"{i}. {c['name']} / {price}荳Ⅸn"

            if detail: msg += f"   {detail}\n"

    else:

        msg += "笨� OK蛟呵｣懊↑縺予n"



    if ng_candidates:

        msg += f"\n笞�ｸ� 蜿り�蛟呵｣�: {len(ng_candidates)}蜷構n"

        for i, (c, ng_reasons, detail) in enumerate(ng_candidates, 1):

            price = normalize_price(c.get("price", 0)) or 0

            msg += f"{i}. {c['name']} / {price}荳Ⅸn"

            msg += f"   NG: {' / '.join(ng_reasons)}\n"

            if detail: msg += f"   {detail}\n"



    if proposal_draft:

        msg += f"\n謠先｡域枚:\n{proposal_draft[:800]}"



    msg += "\n\n"

    if ok_candidates and ng_candidates:

        msg += "縲碁∽ｿ｡縺励※ xxx@yyy.com縲坂�� OK蛟呵｣懊�ｮ縺ｿ\n縲君G繧ょ性繧√※騾∽ｿ｡縺励※ xxx@yyy.com縲坂�� 蜈ｨ蜩｡"

    elif ok_candidates:

        msg += "縲碁∽ｿ｡縺励※ xxx@yyy.com縲阪〒諢丞髄遒ｺ隱阪Γ繝ｼ繝ｫ繧帝√ｊ縺ｾ縺�"

    else:

        msg += "縲君G繧ょ性繧√※騾∽ｿ｡縺励※ xxx@yyy.com縲阪〒蜿り�蛟呵｣懊ｒ騾√ｌ縺ｾ縺�"



    return msg





def build_reverse_match_message(eng_name, matches):

    if not matches:

        return f"搭 逋ｻ骭ｲ螳御ｺ�: {eng_name}\n\n笞�ｸ� 繝槭ャ繝√☆繧句供髮�荳ｭ譯井ｻｶ縺ｪ縺�"



    msg = f"搭 逋ｻ骭ｲ螳御ｺ�: {eng_name}\n\n博 繝槭ャ繝√☆繧区｡井ｻｶ {len(matches)}莉ｶ\n"

    for i, m in enumerate(matches[:3], 1):

        pname = m.get("project_name", "荳肴��")

        pprice = m.get("project_price", 0)

        gross = m.get("gross_profit", 0)

        score = m.get("score", 0)

        req_match = m.get("required_match", {})

        req_str = " ".join(f"{'笳�' if v else 'ﾃ�'}{k}" for k, v in req_match.items()) if req_match else ""



        msg += f"\n{i}. {pname}\n"

        msg += f"   譯井ｻｶ蜊倅ｾ｡: {pprice}荳� / 邊怜茜莠域Φ: {gross}荳� / 繧ｹ繧ｳ繧｢: {score}\n"

        if req_str: msg += f"   蠢�鬆�: {req_str}\n"



    if len(matches) > 3:

        msg += f"\n...莉本len(matches)-3}莉ｶ"



    return msg





def run_double_check(proposal_text, candidates_info):

    system = """SES proposal double-checker. Reply JSON only.

Check for:

1. Forbidden words: 蠑顔､ｾ, 蜈�雜ｳ, 蜊ｳ謌ｦ蜉�, 謨吶∴縺ｦ縺上□縺輔＞

2. Wrong honorifics

3. Unmasked company/person names in proposal body

Return: {"ok": true, "issues": [], "corrected": "same as input if ok"}

If issues found, return corrected text with fixes applied."""



    import json as _json

    result = call_claude(system, _json.dumps({"proposal": proposal_text[:1000], "candidates": candidates_info}, ensure_ascii=False), max_tokens=1000)

    try:

        result_obj = _json.loads(re.sub(r'```json|```', '', result).strip())

        if not isinstance(result_obj, dict):

            return True, [], proposal_text

        return result_obj.get("ok", True), result_obj.get("issues", []), result_obj.get("corrected", proposal_text)

    except Exception as e:

        print(f"[run_double_check] parse error: {e}")

        return True, [], proposal_text





def notion_query(db_id, filter_obj=None):

    results, payload = [], {"page_size": 100}

    if filter_obj: payload["filter"] = filter_obj

    while True:

        r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query",

                         headers=NOTION_HEADERS, json=payload)

        data = r.json()

        results.extend(data.get("results", []))

        if not data.get("has_more"): break

        payload["start_cursor"] = data["next_cursor"]

    return results





def get_database_property_names(db_id):

    if not db_id:

        return set()

    if db_id not in DB_PROPERTY_CACHE:

        try:

            r = requests.get(f"https://api.notion.com/v1/databases/{db_id}",

                             headers=NOTION_HEADERS, timeout=30)

            if r.status_code == 200:

                DB_PROPERTY_CACHE[db_id] = set(r.json().get("properties", {}).keys())

            else:

                print(f"[Notion schema skip] {r.status_code}: {r.text[:120]}")

                DB_PROPERTY_CACHE[db_id] = set()

        except Exception as e:

            print(f"[Notion schema error] {e}")

            DB_PROPERTY_CACHE[db_id] = set()

    return DB_PROPERTY_CACHE[db_id]



def add_input_source_property(props, db_id, input_source):

    if input_source and "蜈･蜉帛��" in get_database_property_names(db_id):

        props["蜈･蜉帛��"] = {"select": {"name": input_source}}



def find_prefecture_from_text(text):

    if not text:

        return ""

    candidates = []

    for pref in ALL_PREFECTURES:

        pos = text.find(pref)

        if pos >= 0:

            candidates.append((pos, pref))

    for alias, pref in PREFECTURE_ALIASES.items():

        pos = text.find(alias)

        if pos >= 0:

            candidates.append((pos, pref))

    if not candidates:

        return ""

    candidates.sort(key=lambda item: item[0])

    return candidates[0][1]



def build_engineer_location_text(info, raw_text):

    fields = [
        info.get("location", ""),
        info.get("station", ""),
        info.get("nearest_station", ""),
        info.get("home", ""),
        info.get("address", ""),
        info.get("note", ""),
        raw_text or "",
    ]

    return "\n".join(str(v) for v in fields if v)



def validate_engineer_for_registration(info, raw_text):

    name = str(info.get("name") or "").strip()

    if not name or name.lower() == "(no name)":

        print(f"[SKIP] name not found: {(raw_text or '')[:100]}")

        return False, "name_not_found"

    pref = find_prefecture_from_text(build_engineer_location_text(info, raw_text))

    if pref and pref not in KANTO_CHUBU_PREFECTURES:

        print(f"[SKIP] area out of scope: {pref} / {(raw_text or '')[:100]}")

        return False, "area_out_of_scope"

    return True, ""



def register_engineer(info, raw_text, sender, user_id=""):

    valid, skip_reason = validate_engineer_for_registration(info, raw_text)

    if not valid:

        return False, skip_reason

    name = str(info.get("name") or "").strip()

    note = f"[LINE auto-register: {sender}]\n{info.get('note', raw_text[:1500])}"

    props = {

        "蜷榊燕": {"title": [{"text": {"content": name}}]},

        "遞ｼ蜒咲憾豕�": {"select": {"name": "遞ｼ蜒榊庄閭ｽ"}},

        "蛯呵��ｼ�LINE繝｡繝｢�ｼ�": {"rich_text": [{"text": {"content": note[:2000]}}]}

    }

    assignee_name = "蟯｡譛ｬ" if user_id and user_id == OKAMOTO_USER_ID else "譚ｾ驥�"
    props["諡�蠖楢�"] = {"select": {"name": assignee_name}}

    skills = [s for s in info.get("skills", []) if s in VALID_SKILLS]

    if skills: props["繧ｹ繧ｭ繝ｫ"] = {"multi_select": [{"name": s} for s in skills]}

    price_val = normalize_price(info.get("price", 0))

    if price_val: props["蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�"] = {"number": price_val}

    if info.get("experience_years"): props["邨碁ｨ灘ｹｴ謨ｰ"] = {"number": info["experience_years"]}

    if info.get("affiliation"):
        props["謇螻樔ｼ夂､ｾ"] = {"rich_text": [{"text": {"content": info["affiliation"][:500]}}]}

    if info.get("contact_name"):
        props["謇螻樊球蠖楢�蜷�"] = {"rich_text": [{"text": {"content": info["contact_name"][:100]}}]}

    if info.get("contact_email"):
        props["謇螻槭Γ繝ｼ繝ｫ"] = {"email": info["contact_email"]}

    add_input_source_property(props, NOTION_ENGINEER_DB_ID, get_line_source_label(user_id))

    res = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS,

                       json={"parent": {"database_id": NOTION_ENGINEER_DB_ID}, "properties": props})

    print(f"register_engineer status: {res.status_code}")

    if res.status_code == 200:

        return True, res.json()["id"]

    print(res.text[:300])

    return False, ""





def register_project(info, raw_text, sender, user_id=""):

    name = info.get("name") or "(no name)"

    note = f"[LINE auto-register: {sender}]\n{info.get('note', raw_text[:1500])}"

    props = {

        "譯井ｻｶ蜷�": {"title": [{"text": {"content": name}}]},

        "繧ｹ繝�繝ｼ繧ｿ繧ｹ": {"select": {"name": "遞ｼ蜒堺ｸｭ"}},

        "譯井ｻｶ隧ｳ邏ｰ": {"rich_text": [{"text": {"content": note[:2000]}}]}

    }

    assignee_name = "蟯｡譛ｬ" if user_id and user_id == OKAMOTO_USER_ID else "譚ｾ驥�"
    props["諡�蠖楢�"] = {"select": {"name": assignee_name}}

    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]

    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]

    if req: props["蠢�隕√せ繧ｭ繝ｫ"] = {"multi_select": [{"name": s} for s in req]}

    if opt: props["蟆壼庄繧ｹ繧ｭ繝ｫ"] = {"multi_select": [{"name": s} for s in opt]}

    price_val = normalize_price(info.get("price", 0))

    if price_val: props["蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�"] = {"number": price_val}

    if info.get("location"): props["蜍､蜍吝慍"] = {"rich_text": [{"text": {"content": info["location"]}}]}

    if info.get("period"): props["譛滄俣"] = {"rich_text": [{"text": {"content": info["period"]}}]}

    add_input_source_property(props, NOTION_PROJECT_DB_ID, get_line_source_label(user_id))

    res = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS,

                       json={"parent": {"database_id": NOTION_PROJECT_DB_ID}, "properties": props})

    print(f"register_project status: {res.status_code}")

    if res.status_code == 200:

        return True, res.json()["id"]

    print(res.text[:300])

    return False, ""





def get_available_engineers():

    pages = notion_query(NOTION_ENGINEER_DB_ID, {

        "property": "遞ｼ蜒咲憾豕�", "select": {"equals": "遞ｼ蜒榊庄閭ｽ"}

    })

    result = []

    for p in pages:

        props = p["properties"]

        name_items = props.get("蜷榊燕", {}).get("title", [])

        name = name_items[0].get("plain_text", "unknown") if name_items else "unknown"

        skills = [o["name"] for o in props.get("繧ｹ繧ｭ繝ｫ", {}).get("multi_select", [])]

        price = props.get("蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�", {}).get("number", 0) or 0

        note_items = props.get("蛯呵��ｼ�LINE繝｡繝｢�ｼ�", {}).get("rich_text", [])

        note = note_items[0].get("plain_text", "") if note_items else ""

        source = "unknown"

        if "line auto-register: matsuno" in note.lower(): source = "matsuno"

        elif "line auto-register: okamoto" in note.lower(): source = "okamoto"

        result.append({"name": name, "skills": skills, "price": price, "note": note[:300], "source": source})

    return result





def get_active_projects():
    # 蜍滄寔荳ｭ繝ｻ遞ｼ蜒堺ｸｭ繝ｻ驕ｸ閠�荳ｭ縺吶∋縺ｦ繧偵�槭ャ繝√Φ繧ｰ蟇ｾ雎｡縺ｨ縺吶ｋ
    pages = notion_query(NOTION_PROJECT_DB_ID, {
        "or": [
            {"property": "繧ｹ繝�繝ｼ繧ｿ繧ｹ", "select": {"equals": "蜍滄寔荳ｭ"}},
            {"property": "繧ｹ繝�繝ｼ繧ｿ繧ｹ", "select": {"equals": "遞ｼ蜒堺ｸｭ"}},
            {"property": "繧ｹ繝�繝ｼ繧ｿ繧ｹ", "select": {"equals": "驕ｸ閠�荳ｭ"}}
        ]
    })

    result = []

    for p in pages:

        props = p["properties"]

        name_items = props.get("譯井ｻｶ蜷�", {}).get("title", [])

        name = name_items[0].get("plain_text", "unknown") if name_items else "unknown"

        req_skills = [o["name"] for o in props.get("蠢�隕√せ繧ｭ繝ｫ", {}).get("multi_select", [])]

        opt_skills = [o["name"] for o in props.get("蟆壼庄繧ｹ繧ｭ繝ｫ", {}).get("multi_select", [])]

        price = props.get("蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�", {}).get("number", 0) or 0

        location_items = props.get("蜍､蜍吝慍", {}).get("rich_text", [])

        location = location_items[0].get("plain_text", "") if location_items else ""

        result.append({

            "name": name,

            "required_skills": req_skills,

            "optional_skills": opt_skills,

            "price": price,

            "location": location,

        })

    return result





def send_email_via_callback(account, to_addr, subject, body):

    import smtplib, ssl

    from email.mime.text import MIMEText

    from email.header import Header as EmailHeader



    accounts_cfg = {

        'matsuno': {'user': 'r-matsuno@terra-ltd.co.jp', 'pw': os.environ.get('MATSUNO_MAIL_PASSWORD', os.environ.get('SESSALES_MAIL_PASSWORD', ''))},

        'okamoto': {'user': 'r-okamoto@terra-ltd.co.jp', 'pw': os.environ.get('OKAMOTO_MAIL_PASSWORD', os.environ.get('SESSALES_MAIL_PASSWORD', ''))},

        'sessales': {'user': 'sessales@terra-ltd.co.jp', 'pw': os.environ.get('SESSALES_MAIL_PASSWORD', '')},

    }

    acc = accounts_cfg.get(account, accounts_cfg['sessales'])

    user, pw = acc['user'], acc['pw']

    if not pw:

        print(f"[send_email] ERROR: 繝代せ繝ｯ繝ｼ繝画悴險ｭ螳� account={account}")

        return False

    try:

        msg = MIMEText(body, 'plain', 'utf-8')

        msg['Subject'] = EmailHeader(subject, 'utf-8')

        msg['From'] = user

        msg['To'] = to_addr

        ctx = ssl.create_default_context()

        with smtplib.SMTP_SSL('mail65.onamae.ne.jp', 465, context=ctx) as s:

            s.login(user, pw)

            s.sendmail(user, [to_addr], msg.as_bytes())

        print(f"[send_email] SENT OK to={to_addr} from={user}")

        return True

    except Exception as e:

        print(f"[send_email] ERROR: {e}")

        return False





def reply_message(reply_token, text, token):

    if len(text) > 4900: text = text[:4900] + "\n...(truncated)"

    requests.post("https://api.line.me/v2/bot/message/reply",

        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},

        json={"replyToken": reply_token, "messages": [{"type": "text", "text": text}]})





def push_message(user_id, text, token):

    if not user_id: return

    if len(text) > 4900: text = text[:4900] + "\n...(truncated)"

    requests.post("https://api.line.me/v2/bot/message/push",

        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},

        json={"to": user_id, "messages": [{"type": "text", "text": text}]})




# 笏笏 繧ｹ繝�繝ｼ繧ｿ繧ｹ逡･隱槭�槭ャ繝斐Φ繧ｰ 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
STATUS_ALIASES = {
    "蜑�": "諢丞髄遒ｺ隱榊燕",
    "遒ｺ隱�": "諢丞髄遒ｺ隱堺ｸｭ", "遒ｺ隱堺ｸｭ": "諢丞髄遒ｺ隱堺ｸｭ", "縺�縺薙≧": "諢丞髄遒ｺ隱堺ｸｭ",
    "髱｢隲�": "髱｢隲�蟶梧悍", "髱｢隲�蟶梧悍": "髱｢隲�蟶梧悍", "蟶梧悍": "髱｢隲�蟶梧悍",
    "隱ｿ謨ｴ": "髱｢隲�隱ｿ謨ｴ荳ｭ", "隱ｿ謨ｴ荳ｭ": "髱｢隲�隱ｿ謨ｴ荳ｭ",
    "貂�": "髱｢隲�貂医∩", "髱｢隲�貂�": "髱｢隲�貂医∩", "貂医∩": "髱｢隲�貂医∩",
    "蜷域ｼ": "蜷域ｼ", "ok": "蜷域ｼ", "OK": "蜷域ｼ", "縲�": "蜷域ｼ",
    "ng": "NG", "NG": "NG", "ﾃ�": "NG", "縺ｰ縺､": "NG",
}

def normalize_status(raw):
    """逡･隱槭ｒ繧ｹ繝�繝ｼ繧ｿ繧ｹ豁｣蠑丞錐縺ｫ螟画鋤"""
    return STATUS_ALIASES.get(raw.strip(), raw.strip())

def normalize_candidate_name(raw):
    """繧､繝九す繝｣繝ｫ繝ｻ逡･遘ｰ繧呈ｭ｣隕丞喧�ｼ医ラ繝�繝医�ｻ繧ｹ繝壹�ｼ繧ｹ髯､蜴ｻ繝ｻ螟ｧ譁�蟄怜喧�ｼ�"""
    return raw.replace(".", "").replace(" ", "").replace("縲", "").upper()

def find_candidate_in_text(text, name_query):
    """譯井ｻｶ隧ｳ邏ｰ繝�繧ｭ繧ｹ繝医°繧牙呵｣懆�陦後ｒ謗｢縺呻ｼ磯Κ蛻�荳閾ｴ�ｼ�"""
    nq = normalize_candidate_name(name_query)
    for line in text.split("\n"):
        if "笆ｶ" not in line:
            continue
        # 陦後°繧牙呵｣懆�蜷埼Κ蛻�繧呈歓蜃ｺ�ｼ育分蜿ｷ縺ｨ蜊倅ｾ｡縺ｮ髢難ｼ�
        m = re.search(r"\d+\.\s+(.+?)\s+/", line)
        if m:
            cname = m.group(1).strip()
            if nq in normalize_candidate_name(cname):
                return line, cname
    return None, None

def update_candidate_status(page_id, candidate_name, new_status):
    """譯井ｻｶ隧ｳ邏ｰ縺ｮ蛟呵｣懆�繧ｹ繝�繝ｼ繧ｿ繧ｹ繧呈峩譁ｰ縺吶ｋ"""
    r = requests.get(f"https://api.notion.com/v1/pages/{page_id}",
                     headers=NOTION_HEADERS, timeout=10)
    if r.status_code != 200:
        return False, f"譯井ｻｶ蜿門ｾ怜､ｱ謨�: {r.status_code}"

    props = r.json().get("properties", {})
    existing_items = props.get("譯井ｻｶ隧ｳ邏ｰ", {}).get("rich_text", [])
    existing_text = existing_items[0].get("plain_text", "") if existing_items else ""

    if not existing_text or "縲仙呵｣懆�繧ｹ繝�繝ｼ繧ｿ繧ｹ" not in existing_text:
        return False, "蛟呵｣懆�繧ｹ繝�繝ｼ繧ｿ繧ｹ谺�縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ"

    matched_line, matched_name = find_candidate_in_text(existing_text, candidate_name)
    if not matched_line:
        return False, f"縲鶏candidate_name}縲阪′隕九▽縺九ｊ縺ｾ縺帙ｓ"

    new_line = re.sub(r"笆ｶ .+$", f"笆ｶ {new_status}", matched_line)
    updated_text = existing_text.replace(matched_line, new_line)[:1900]

    r2 = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=NOTION_HEADERS,
        json={"properties": {"譯井ｻｶ隧ｳ邏ｰ": {"rich_text": [{"type": "text", "text": {"content": updated_text}}]}}},
        timeout=10
    )
    if r2.status_code == 200:
        return True, matched_name
    return False, f"譖ｴ譁ｰ螟ｱ謨�: {r2.status_code}"


def find_projects_with_candidate(name_query):
    """蛟呵｣懆�蜷阪〒蜈ｨ譯井ｻｶ繧呈ｨｪ譁ｭ讀懃ｴ｢縺励※繝偵ャ繝医＠縺�(page_id, proj_name, matched_name)繧定ｿ斐☆"""
    pages = notion_query(NOTION_PROJECT_DB_ID, {
        "or": [
            {"property": "繧ｹ繝�繝ｼ繧ｿ繧ｹ", "select": {"equals": "蜍滄寔荳ｭ"}},
            {"property": "繧ｹ繝�繝ｼ繧ｿ繧ｹ", "select": {"equals": "遞ｼ蜒堺ｸｭ"}},
            {"property": "繧ｹ繝�繝ｼ繧ｿ繧ｹ", "select": {"equals": "驕ｸ閠�荳ｭ"}},
        ]
    })
    results = []
    for p in pages:
        props = p.get("properties", {})
        name_items = props.get("譯井ｻｶ蜷�", {}).get("title", [])
        proj_name = name_items[0].get("plain_text", "") if name_items else ""
        detail_items = props.get("譯井ｻｶ隧ｳ邏ｰ", {}).get("rich_text", [])
        detail_text = detail_items[0].get("plain_text", "") if detail_items else ""
        if "縲仙呵｣懆�繧ｹ繝�繝ｼ繧ｿ繧ｹ" not in detail_text:
            continue
        matched_line, matched_name = find_candidate_in_text(detail_text, name_query)
        if matched_line:
            results.append((p["id"], proj_name, matched_name))
    return results


def build_matching_result_reply():
    """Notion DB縺九ｉ繝ｪ繧｢繝ｫ繧ｿ繧､繝縺ｧ繝槭ャ繝√Φ繧ｰ邨先棡繧貞叙蠕励＠縺ｦ繝輔か繝ｼ繝槭ャ繝�"""
    try:
        # 繧｢繧ｯ繝�繧｣繝悶↑譯井ｻｶ繧貞叙蠕�
        project_pages = notion_query(NOTION_PROJECT_DB_ID, {
            "or": [
                {"property": "繧ｹ繝�繝ｼ繧ｿ繧ｹ", "select": {"equals": "蜍滄寔荳ｭ"}},
                {"property": "繧ｹ繝�繝ｼ繧ｿ繧ｹ", "select": {"equals": "遞ｼ蜒堺ｸｭ"}},
            ]
        })
        # 遞ｼ蜒榊庄閭ｽ縺ｪ繧ｨ繝ｳ繧ｸ繝九い繧貞叙蠕�
        engineer_pages = notion_query(NOTION_ENGINEER_DB_ID, {
            "property": "遞ｼ蜒咲憾豕�", "select": {"equals": "遞ｼ蜒榊庄閭ｽ"}
        })
    except Exception as e:
        print(f"[matching_reply] notion error: {e}")
        return "縲舌�槭ャ繝√Φ繧ｰ邨先棡縲曾n繝�繝ｼ繧ｿ蜿門ｾ怜､ｱ謨�"

    if not project_pages or not engineer_pages:
        return f"縲舌�槭ャ繝√Φ繧ｰ邨先棡縲捜datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n譯井ｻｶ縺ｾ縺溘�ｯ莠ｺ譚舌ョ繝ｼ繧ｿ縺ｪ縺暦ｼ域｡井ｻｶ:{len(project_pages)}莉ｶ 莠ｺ譚�:{len(engineer_pages)}蜷搾ｼ�"

    number_labels = ["竭", "竭｡", "竭｢", "竭｣", "竭､", "竭･", "竭ｦ", "竭ｧ", "竭ｨ", "竭ｩ"]
    lines = [f"縲舌�槭ャ繝√Φ繧ｰ邨先棡縲捜datetime.now().strftime('%Y-%m-%d %H:%M')}"]
    match_count = 0

    for pp in project_pages:
        props = pp.get("properties", {})
        # 譯井ｻｶ蜷�
        name_items = props.get("譯井ｻｶ蜷�", {}).get("title", [])
        proj_name = name_items[0].get("plain_text", "蜷咲ｧｰ譛ｪ險ｭ螳�") if name_items else "蜷咲ｧｰ譛ｪ險ｭ螳�"
        # 蠢�鬆医せ繧ｭ繝ｫ
        req_skills = [o["name"] for o in props.get("蠢�隕√せ繧ｭ繝ｫ", {}).get("multi_select", [])]
        proj_price = props.get("蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�", {}).get("number") or 0
        notion_url = f"https://www.notion.so/{pp['id'].replace('-', '')}"

        if not req_skills:
            continue  # 繧ｹ繧ｭ繝ｫ謖�螳壹↑縺玲｡井ｻｶ縺ｯ繧ｹ繧ｭ繝�繝�

        # 繧ｨ繝ｳ繧ｸ繝九い縺ｨ縺ｮ繧ｹ繧ｭ繝ｫ繝槭ャ繝√Φ繧ｰ
        matched = []
        for ep in engineer_pages:
            eprops = ep.get("properties", {})
            ename_items = eprops.get("蜷榊燕", {}).get("title", [])
            ename = ename_items[0].get("plain_text", "荳肴��") if ename_items else "荳肴��"
            eskills = [o["name"] for o in eprops.get("繧ｹ繧ｭ繝ｫ", {}).get("multi_select", [])]
            eprice = eprops.get("蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�", {}).get("number") or 0

            # 蠢�鬆医せ繧ｭ繝ｫ縺�1縺､莉･荳贋ｸ閾ｴ縺吶ｌ縺ｰ繝槭ャ繝√→縺吶ｋ
            hit = [s for s in req_skills if s in eskills]
            if not hit:
                continue
            # 邊怜茜繝√ぉ繝�繧ｯ�ｼ�5荳�莉･荳奇ｼ�
            if eprice > 0 and proj_price > 0 and (proj_price - eprice) < 5:
                continue
            matched.append({"name": ename, "price": eprice, "hit": hit})

        if not matched:
            continue

        lines.append("")
        lines.append(f"笆 {proj_name}�ｼ�{len(matched)}蜷阪�槭ャ繝��ｼ�")
        lines.append(notion_url)
        for idx, m in enumerate(matched[:2]):
            price_str = f"{m['price']}荳�" if m['price'] else "譛ｪ險ｭ螳�"
            lines.append(f"  {number_labels[idx]} {m['name']} /{price_str}")
        if len(matched) > 2:
            lines.append(f"  莉本len(matched)-2}蜷�")
        match_count += 1

    if match_count == 0:
        return f"縲舌�槭ャ繝√Φ繧ｰ邨先棡縲捜datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n迴ｾ蝨ｨ繝槭ャ繝√Φ繧ｰ蛟呵｣懊↑縺予n�ｼ域｡井ｻｶ:{len(project_pages)}莉ｶ 莠ｺ譚�:{len(engineer_pages)}蜷阪〒讀懃ｴ｢貂医∩�ｼ�"

    return "\n".join(lines)



def build_progress_reply():
    """譯井ｻｶ騾ｲ謐励ｒReply API逕ｨ縺ｫ繝輔か繝ｼ繝槭ャ繝�"""
    try:
        pages = notion_query(NOTION_PROJECT_DB_ID, {
            "or": [
                {"property": "繧ｹ繝�繝ｼ繧ｿ繧ｹ", "select": {"equals": "蜍滄寔荳ｭ"}},
                {"property": "繧ｹ繝�繝ｼ繧ｿ繧ｹ", "select": {"equals": "驕ｸ閠�荳ｭ"}},
            ]
        })
    except Exception as e:
        print(f"[progress] notion error: {e}")
        return "縲先｡井ｻｶ騾ｲ謐励曾n繝�繝ｼ繧ｿ蜿門ｾ怜､ｱ謨�"

    weekdays = ["譛�","轣ｫ","豌ｴ","譛ｨ","驥�","蝨�","譌･"]
    now = datetime.now()
    header = f"縲先｡井ｻｶ騾ｲ謐励捜now.strftime('%m/%d')}�ｼ�{weekdays[now.weekday()]}�ｼ�"
    lines = [header, ""]

    action_lines = []

    if not pages:
        lines.append("譛ｬ譌･蜍滄寔荳ｭ譯井ｻｶ縺ｪ縺�")
        return "\n".join(lines)

    for p in pages:
        props = p.get("properties", {})
        name_items = props.get("譯井ｻｶ蜷�", {}).get("title", [])
        name = name_items[0].get("plain_text", "蜷咲ｧｰ譛ｪ險ｭ螳�") if name_items else "蜷咲ｧｰ譛ｪ險ｭ螳�"
        price = props.get("蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�", {}).get("number")
        if price is None:
            price = props.get("蜊倅ｾ｡(荳�蜀�)", {}).get("number")
        if isinstance(price, float) and price.is_integer():
            price = int(price)
        price_str = str(price) if price not in (None, "") else "-"

        teian    = props.get("謠先｡井ｸｭ",   {}).get("number") or 0
        mendan   = props.get("髱｢隲�蟶梧悍", {}).get("number") or 0
        ng       = props.get("NG",       {}).get("number") or 0
        goukaku  = props.get("蜷域ｼ",     {}).get("number") or 0
        seiyaku  = props.get("謌千ｴ�",     {}).get("number") or 0
        eigyo_end = props.get("蝟ｶ讌ｭ邨ゆｺ�", {}).get("number") or 0

        lines.append(f"笆 {name}�ｼ�{price_str}荳��ｼ�")
        row = f"  謠先｡井ｸｭ:{teian} / 髱｢隲�蟶梧悍:{mendan} / NG:{ng} / 蜷域ｼ:{goukaku}"
        if seiyaku:
            row += f" / 謌千ｴ�:{seiyaku}"
        if eigyo_end:
            row += f" / 蝟ｶ讌ｭ邨ゆｺ�:{eigyo_end}"
        lines.append(row)
        lines.append("")

        if mendan > 0:
            action_lines.append(f"  {name} 竊� 髱｢隲�蟶梧悍{mendan}莉ｶ")

    lines.append("笞｡ 隕√い繧ｯ繧ｷ繝ｧ繝ｳ")
    if action_lines:
        lines.extend(action_lines)
    else:
        lines.append("  縺ｪ縺�")

    return "\n".join(lines).rstrip()

def split_line_message(text, limit=4900):

    chunks = []

    current = ""

    for line in text.splitlines():

        next_line = line if not current else current + "\n" + line

        if len(next_line) <= limit:

            current = next_line

            continue

        if current:

            chunks.append(current)

        current = line

    if current:

        chunks.append(current)

    return chunks or [text[:limit]]





def handle_file_message(message_id, mime_type, reply_token, sender, sender_token):

    """LINE縺九ｉ騾√ｉ繧後◆PDF/逕ｻ蜒上ヵ繧｡繧､繝ｫ繧痴kill_reader_api縺ｧ蜃ｦ逅�"""

    try:

        # LINE縺九ｉ繝輔ぃ繧､繝ｫ繧ｳ繝ｳ繝�繝ｳ繝�蜿門ｾ�

        token = MATSUNO_CHANNEL_TOKEN if sender == "matsuno" else OKAMOTO_CHANNEL_TOKEN

        res = requests.get(

            f"https://api-data.line.me/v2/bot/message/{message_id}/content",

            headers={"Authorization": f"Bearer {token}"},

            timeout=30

        )

        if res.status_code != 200:

            reply_message(reply_token, f"笶� 繝輔ぃ繧､繝ｫ蜿門ｾ怜､ｱ謨�: {res.status_code}", sender_token)

            return



        b64_data = base64.b64encode(res.content).decode()



        # skill_reader_api�ｼ�8766�ｼ峨↓騾∽ｿ｡

        reply_message(reply_token, "搭 繧ｹ繧ｭ繝ｫ繧ｷ繝ｼ繝郁ｧ｣譫蝉ｸｭ...", sender_token)

        api_res = requests.post(

            "http://127.0.0.1:8766/process_skill_sheet",

            json={"base64": b64_data, "mime": mime_type, "affiliation": "雋ｴ遉ｾ"},

            timeout=120

        )



        if api_res.status_code != 200:

            reply_message(reply_token, f"笶� 隗｣譫仙､ｱ謨�: {api_res.text[:200]}", sender_token)

            return



        result = api_res.json()

        if result.get("status") != "ok":

            reply_message(reply_token, f"笶� 隗｣譫舌お繝ｩ繝ｼ: {result.get('message','荳肴��')}", sender_token)

            return



        eng = result.get("engineer", {})

        name = eng.get("name", "荳肴��")

        skills = ", ".join(eng.get("skills", [])) or "縺ｪ縺�"

        level = eng.get("level", "荳肴��")

        summary = eng.get("summary", "")

        just_count = result.get("just_count", 0)

        iko_mail = result.get("iko_mail", "")



        # 邨先棡繧単ENDING_SKILL_MAIL縺ｫ菫晏ｭ�

        pending_key = sender + "_skill"

        PENDING_SKILL_MAIL[pending_key] = iko_mail



        msg = f"搭 繧ｹ繧ｭ繝ｫ繧ｷ繝ｼ繝郁ｧ｣譫仙ｮ御ｺ�\n"

        msg += f"豌丞錐: {name}\n"

        msg += f"繝ｬ繝吶Ν: {level}\n"

        msg += f"繧ｹ繧ｭ繝ｫ: {skills}\n"

        if summary:

            msg += f"讎りｦ�: {summary}\n"

        msg += f"\n邊怜茜繧ｸ繝｣繧ｹ繝域｡井ｻｶ�ｼ�5縲�12荳��ｼ�: {just_count}莉ｶ\n"

        msg += "\n縲後Γ繝ｼ繝ｫ騾∽ｿ｡縺励※ xxx@yyy.com縲阪〒諢丞髄遒ｺ隱阪Γ繝ｼ繝ｫ繧帝∽ｿ｡縺ｧ縺阪∪縺吶�"



        push_message(

            MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID,

            msg,

            sender_token

        )



    except Exception as e:

        push_message(

            MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID,

            f"笶� 繧ｹ繧ｭ繝ｫ繧ｷ繝ｼ繝亥�ｦ逅�繧ｨ繝ｩ繝ｼ: {str(e)[:200]}",

            sender_token

        )

        traceback.print_exc()





def handle_sheet_url(url, reply_token, sender, sender_token):

    reply_message(reply_token, "売 繧ｹ繝励Ξ繝�繝峨す繝ｼ繝医ｒ蜿門ｾ嶺ｸｭ...", sender_token)

    result = fetch_sheet_text(url)

    if result["status"] == "login_required":

        reply_message(reply_token, "笞�ｸ� 繝ｭ繧ｰ繧､繝ｳ縺悟ｿ�隕√↑繧ｹ繝励Ξ繝�繝峨す繝ｼ繝医�ｮ縺溘ａ繧ｹ繧ｭ繝�繝励＠縺ｾ縺励◆", sender_token)

        return

    elif result["status"] == "error":

        reply_message(reply_token, f"笶� 繧ｹ繝励Ξ繝�繝峨す繝ｼ繝亥叙蠕怜､ｱ謨�: {result.get('error','')[:100]}", sender_token)

        return



    text = result.get("text", "")

    if not text or len(text.strip()) < 50:

        reply_message(reply_token, "笞�ｸ� 繧ｹ繝励Ξ繝�繝峨す繝ｼ繝医�ｮ蜀�螳ｹ縺悟叙蠕励〒縺阪∪縺帙ｓ縺ｧ縺励◆", sender_token)

        return



    content_type = classify_sheet_content(text)

    raw_text = f"[繧ｹ繝励Ξ繝�繝峨す繝ｼ繝�: {url}]\n{text}"



    if content_type == "project":

        projects = extract_projects_from_text(text)

        if not projects:

            reply_message(reply_token, "笞�ｸ� 譯井ｻｶ諠�蝣ｱ縺梧歓蜃ｺ縺ｧ縺阪∪縺帙ｓ縺ｧ縺励◆", sender_token)

            return

        success_count = skip_count = 0

        for proj in projects:

            ok, _ = register_project(proj, raw_text, sender)

            if ok: success_count += 1

            else: skip_count += 1

        msg = f"投 繧ｹ繝励Ξ繝�繝峨す繝ｼ繝医°繧画｡井ｻｶ逋ｻ骭ｲ螳御ｺ�\n\n逋ｻ骭ｲ: {success_count}莉ｶ / 繧ｹ繧ｭ繝�繝�: {skip_count}莉ｶ\n"

        for i, p in enumerate(projects[:5], 1):

            msg += f"{i}. {p.get('name','(no name)')} / {p.get('price',0)}荳Ⅸn"

        if len(projects) > 5: msg += f"...莉本len(projects)-5}莉ｶ"

        reply_message(reply_token, msg, sender_token)

    else:

        engineers = extract_engineers_from_text(text)

        if not engineers:

            reply_message(reply_token, "笞�ｸ� 莠ｺ蜩｡諠�蝣ｱ縺梧歓蜃ｺ縺ｧ縺阪∪縺帙ｓ縺ｧ縺励◆", sender_token)

            return

        success_count = skip_count = 0

        skip_reasons = set()

        registered = []

        for eng in engineers:

            ok, reason = register_engineer(eng, raw_text, sender)

            if ok:

                success_count += 1

                registered.append(eng)

            else:

                skip_count += 1

                if reason:

                    skip_reasons.add(reason)

        msg = f"投 繧ｹ繝励Ξ繝�繝峨す繝ｼ繝医°繧我ｺｺ蜩｡逋ｻ骭ｲ螳御ｺ�\n\n逋ｻ骭ｲ: {success_count}蜷� / 繧ｹ繧ｭ繝�繝�: {skip_count}蜷構n"

        if "name_not_found" in skip_reasons:

            msg += f"{ENGINEER_NAME_NOT_FOUND_REPLY}\n"

        if "area_out_of_scope" in skip_reasons:

            msg += f"{AREA_OUT_OF_SCOPE_REPLY}\n"

        for i, e in enumerate(engineers[:5], 1):

            msg += f"{i}. {e.get('name','(no name)')} / {e.get('price',0)}荳Ⅸn"

        if len(engineers) > 5: msg += f"...莉本len(engineers)-5}蜷�"

        if registered:

            active_projects = deduplicate_projects(get_active_projects())

            if active_projects:

                msg += f"\n\n博 {len(registered)}蜷阪�ｮ騾�繝槭ャ繝√Φ繧ｰ荳ｭ..."

                reply_message(reply_token, msg, sender_token)

                for eng in registered[:3]:

                    result_m = run_reverse_matching(eng, active_projects)

                    matches = result_m.get("matches", [])[:3]

                    if matches:
                        if MATCHING_LOGIC_AVAILABLE:
                            rev_msg = build_reverse_match_message_v2(
                                eng.get("name","?"), matches,
                                normalize_price(eng.get("price", 0)) or 0)
                        else:
                            rev_msg = build_reverse_match_message(eng.get("name","?"), matches)
                        push_message(MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID,
                                     rev_msg,
                                     MATSUNO_CHANNEL_TOKEN if sender == "matsuno" else OKAMOTO_CHANNEL_TOKEN)

                return

        reply_message(reply_token, msg, sender_token)





def process_message(text, reply_token, sender, sender_token, user_id=""):

    print(f"[{sender}] {text[:80]}")

    pending_key = sender + "_latest"

    skill_key = sender + "_skill"

    text_stripped = text.strip()


    # 笏笏 繝ｪ繝｢繝ｼ繝医さ繝槭Φ繝会ｼ域收驥弱�ｮ縺ｿ�ｼ俄楳笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    if user_id and user_id == MATSUNO_USER_ID:
        if text_stripped.startswith("/run "):
            result = execute_remote(text_stripped[5:])
            reply_message(reply_token, result, sender_token)
            return
        elif text_stripped.startswith("/bg "):
            result = execute_bg(text_stripped[4:])
            reply_message(reply_token, result, sender_token)
            return
        elif text_stripped == "/log":
            result = get_log()
            reply_message(reply_token, result, sender_token)
            return
        elif text_stripped == "/health":
            result = get_health()
            reply_message(reply_token, result, sender_token)
            return
    elif (
        text_stripped.startswith("/run ")
        or text_stripped.startswith("/bg ")
        or text_stripped in ("/log", "/health")
    ):
        reply_message(reply_token, "笶� 繧ｨ繝ｩ繝ｼ\n讓ｩ髯舌′縺ゅｊ縺ｾ縺帙ｓ", sender_token)
        return



    # 笏笏 騾∽ｿ｡謖�遉ｺ縺ｮ蜃ｦ逅� 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏

    is_send_all = "NG繧ょ性繧√※騾∽ｿ｡" in text_stripped or "NG蜷ｫ繧√※騾∽ｿ｡" in text_stripped

    is_mail_send = "繝｡繝ｼ繝ｫ騾∽ｿ｡縺励※" in text_stripped

    is_send_ok  = text_stripped.startswith("騾∽ｿ｡縺励※") or text_stripped.startswith("騾∽ｿ｡ ")



    # 繧ｹ繧ｭ繝ｫ繧ｷ繝ｼ繝郁ｧ｣譫仙ｾ後�ｮ諢丞髄遒ｺ隱阪Γ繝ｼ繝ｫ騾∽ｿ｡

    if is_mail_send and skill_key in PENDING_SKILL_MAIL:

        emails = EMAIL_PATTERN.findall(text_stripped)

        to_addr = emails[0] if emails else None

        iko_mail = PENDING_SKILL_MAIL[skill_key]

        if to_addr:

            account = "matsuno" if sender == "matsuno" else "okamoto"

            subject = "譯井ｻｶ縺疲､懆ｨ弱�ｮ縺企｡倥＞"

            sent = send_email_via_callback(account, to_addr, subject, iko_mail)

            if sent:

                reply_message(reply_token, f"笨� 諢丞髄遒ｺ隱阪Γ繝ｼ繝ｫ騾∽ｿ｡螳御ｺ�\n騾∽ｿ｡蜈�: {to_addr}", sender_token)

                del PENDING_SKILL_MAIL[skill_key]

            else:

                reply_message(reply_token, f"笶� 騾∽ｿ｡螟ｱ謨励ゆｻ･荳九ｒ繧ｳ繝斐�ｼ縺励※謇句虚騾∽ｿ｡縺励※縺上□縺輔＞:\n螳帛��: {to_addr}\n\n{iko_mail[:2000]}", sender_token)

        else:

            reply_message(reply_token, f"透 騾∽ｿ｡蜈医Γ繝ｼ繝ｫ繧｢繝峨Ξ繧ｹ繧呈欠螳壹＠縺ｦ縺上□縺輔＞\n萓�: 繝｡繝ｼ繝ｫ騾∽ｿ｡縺励※ xxx@yyy.com\n\n{iko_mail[:1500]}", sender_token)

        return



    # 笏笏 繧ｹ繝�繝ｼ繧ｿ繧ｹ譖ｴ譁ｰ繧ｳ繝槭Φ繝会ｼ育ｰ｡逡･迚茨ｼ俄楳笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    # 譖ｸ蠑�: 縲梧峩譁ｰ 蛟呵｣懆�蜷� 繧ｹ繝�繝ｼ繧ｿ繧ｹ逡･隱槭�
    # 萓�:  縲梧峩譁ｰ RH 遒ｺ隱堺ｸｭ縲阪梧峩譁ｰ MY 髱｢隲�縲阪梧峩譁ｰ OA NG縲�
    if text_stripped.startswith("譖ｴ譁ｰ ") or text_stripped.startswith("譖ｴ譁ｰ縲"):
        parts = text_stripped[2:].strip().split()
        if len(parts) < 2:
            reply_message(reply_token,
                "譖ｸ蠑�: 譖ｴ譁ｰ 蛟呵｣懆�蜷� 繧ｹ繝�繝ｼ繧ｿ繧ｹ\n"
                "萓�: 譖ｴ譁ｰ RH 遒ｺ隱堺ｸｭ / 譖ｴ譁ｰ MY 髱｢隲� / 譖ｴ譁ｰ OA NG\n"
                "繧ｹ繝�繝ｼ繧ｿ繧ｹ逡･隱�: 蜑� 遒ｺ隱� 髱｢隲� 隱ｿ謨ｴ 貂� 蜷域ｼ OK NG",
                sender_token)
            return
        name_query = parts[0]
        status_raw = parts[1]
        new_status = normalize_status(status_raw)
        valid = list(STATUS_ALIASES.values()) + list(STATUS_ALIASES.keys())
        if new_status not in ["諢丞髄遒ｺ隱榊燕","諢丞髄遒ｺ隱堺ｸｭ","髱｢隲�蟶梧悍","髱｢隲�隱ｿ謨ｴ荳ｭ","髱｢隲�貂医∩","蜷域ｼ","NG"]:
            reply_message(reply_token,
                f"縲鶏status_raw}縲阪�ｯ辟｡蜉ｹ縺ｧ縺兔n逡･隱�: 蜑� 遒ｺ隱� 髱｢隲� 隱ｿ謨ｴ 貂� 蜷域ｼ OK NG",
                sender_token)
            return
        # 蛟呵｣懆�蜷阪〒譯井ｻｶ繧呈ｨｪ譁ｭ讀懃ｴ｢
        hits = find_projects_with_candidate(name_query)
        if not hits:
            reply_message(reply_token, f"縲鶏name_query}縲阪′蛟呵｣懆�繝ｪ繧ｹ繝医↓隕九▽縺九ｊ縺ｾ縺帙ｓ", sender_token)
            return
        if len(hits) > 1:
            # 隍�謨ｰ譯井ｻｶ縺ｫ縺�繧句ｴ蜷医�ｯ荳隕ｧ繧定ｿ斐☆ 竊� 縲梧峩譁ｰ RH 遒ｺ隱堺ｸｭ Java縲阪〒譯井ｻｶ繧堤ｵ槭ｌ繧区｡亥��
            names = "\n".join(f"{i+1}. {n}�ｼ�{m}�ｼ�" for i, (_, n, m) in enumerate(hits[:5]))
            if len(parts) >= 3:
                # 3縺､逶ｮ縺ｮ蠑墓焚繧呈｡井ｻｶ繧ｭ繝ｼ繝ｯ繝ｼ繝峨→縺励※邨槭ｊ霎ｼ縺ｿ
                proj_kw = parts[2]
                filtered = [(pid, pn, mn) for pid, pn, mn in hits if proj_kw.lower() in pn.lower()]
                if len(filtered) == 1:
                    hits = filtered
                else:
                    reply_message(reply_token,
                        f"隍�謨ｰ譯井ｻｶ縺ｫ繝偵ャ繝�:\n{names}\n\n邨槭ｊ霎ｼ縺ｿ萓�: 譖ｴ譁ｰ {name_query} {status_raw} Java",
                        sender_token)
                    return
            else:
                reply_message(reply_token,
                    f"縲鶏name_query}縲阪�ｯ隍�謨ｰ譯井ｻｶ縺ｫ蛟呵｣應ｸｭ:\n{names}\n\n譯井ｻｶ繧堤ｵ槭ｋ蝣ｴ蜷�: 譖ｴ譁ｰ {name_query} {status_raw} 譯井ｻｶ繧ｭ繝ｼ繝ｯ繝ｼ繝噂n蜈ｨ莉ｶ譖ｴ譁ｰ縺吶ｋ蝣ｴ蜷�: 譖ｴ譁ｰ {name_query} {status_raw} 蜈ｨ驛ｨ",
                    sender_token)
                return
        if len(parts) >= 3 and parts[2] == "蜈ｨ驛ｨ":
            # 蜈ｨ譯井ｻｶ荳諡ｬ譖ｴ譁ｰ
            success_list = []
            for pid, pn, mn in hits:
                ok, result = update_candidate_status(pid, mn, new_status)
                if ok:
                    success_list.append(pn[:20])
            reply_message(reply_token,
                f"笨� {len(success_list)}莉ｶ譖ｴ譁ｰ\n繧ｹ繝�繝ｼ繧ｿ繧ｹ: {new_status}\n" + "\n".join(success_list),
                sender_token)
            return
        page_id, proj_name, matched_name = hits[0]
        ok, result = update_candidate_status(page_id, matched_name, new_status)
        if ok:
            reply_message(reply_token,
                f"笨� {matched_name} 竊� {new_status}\n{proj_name[:30]}",
                sender_token)
        else:
            reply_message(reply_token, f"笶� 譖ｴ譁ｰ螟ｱ謨�: {result}", sender_token)
        return

    # 繝槭ャ繝√Φ繧ｰ邨先棡辣ｧ莨�

    if "繝槭ャ繝√Φ繧ｰ" in text_stripped and len(text_stripped) <= 10:

        matching_reply = build_matching_result_reply()

        chunks = split_line_message(matching_reply)

        reply_message(reply_token, chunks[0], sender_token)

        push_user_id = user_id or (MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID)

        for chunk in chunks[1:]:

            push_message(push_user_id, chunk, sender_token)

        return


    # 譯井ｻｶ騾ｲ謐礼�ｧ莨�

    if "騾ｲ謐�" in text_stripped and len(text_stripped) <= 10:

        progress_reply = build_progress_reply()

        chunks = split_line_message(progress_reply)

        reply_message(reply_token, chunks[0], sender_token)

        push_user_id = user_id or (MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID)

        for chunk in chunks[1:]:

            push_message(push_user_id, chunk, sender_token)

        return


    if is_send_ok or is_send_all:

        pending = PENDING_PROPOSALS.get(pending_key)

        if not pending:

            reply_message(reply_token, "笞�ｸ� 騾∽ｿ｡蠕�縺｡縺ｮ謠先｡医′縺ゅｊ縺ｾ縺帙ｓ", sender_token)

            return



        emails = EMAIL_PATTERN.findall(text_stripped)

        to_addr = emails[0] if emails else None



        ok_list  = pending.get("ok", [])

        ng_list  = pending.get("ng", [])

        draft    = pending.get("proposal_draft", "")

        proj_name = pending.get("proj_name", "譯井ｻｶ")



        target = ok_list + (ng_list if is_send_all else [])

        target_names = [c["name"] for c, *_ in target]



        if to_addr:

            account = "matsuno" if sender == "matsuno" else "okamoto"

            subject = f"縲舌＃謠先｡医捜proj_name}"

            body = draft if draft else f"縲舌＃謠先｡医捜proj_name}\n\n" + "\n".join(f"繝ｻ{n}" for n in target_names)

            sent = send_email_via_callback(account, to_addr, subject, body)

            if sent:

                reply_message(reply_token,

                    f"笨� 繝｡繝ｼ繝ｫ騾∽ｿ｡螳御ｺ�\n騾∽ｿ｡蜈�: {to_addr}\n莉ｶ蜷�: {subject}\n蟇ｾ雎｡: {len(target_names)}蜷�",

                    sender_token)

            else:

                reply_message(reply_token,

                    f"笶� 閾ｪ蜍暮∽ｿ｡螟ｱ謨励ゆｻ･荳九ｒ繧ｳ繝斐�ｼ縺励※謇句虚騾∽ｿ｡縺励※縺上□縺輔＞:\n騾∽ｿ｡蜈�: {to_addr}\n\n{body[:1500]}",

                    sender_token)

        else:

            label = "蜈ｨ蜩｡" if is_send_all else "OK蛟呵｣懊�ｮ縺ｿ"

            reply_message(reply_token,

                f"搭 謠先｡亥��螳ｹ遒ｺ隱搾ｼ�{label} {len(target_names)}蜷搾ｼ噂n騾∽ｿ｡蜈医Γ繝ｼ繝ｫ繧偵碁∽ｿ｡縺励※ xxx@yyy.com縲阪〒謖�螳壹＠縺ｦ縺上□縺輔＞\n\n{draft[:1500]}",

                sender_token)

            return



        del PENDING_PROPOSALS[pending_key]

        return



    # 笏笏 繧ｹ繝励Ξ繝�繝峨す繝ｼ繝�URL 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏

    sheet_urls = SHEET_URL_PATTERN.findall(text)

    if sheet_urls:

        handle_sheet_url(sheet_urls[0], reply_token, sender, sender_token)

        return



    # 笏笏 騾壼ｸｸ繝｡繝�繧ｻ繝ｼ繧ｸ蛻�鬘� 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏

    info = classify_message(text)

    msg_type = info.get("type", "other")

    print(f"[type] {msg_type}")



    if msg_type == "engineer":

        success, reason = register_engineer(info, text, sender, user_id=user_id)

        if not success:

            if reason == "name_not_found":

                reply_message(reply_token, ENGINEER_NAME_NOT_FOUND_REPLY, sender_token)

                return

            if reason == "area_out_of_scope":

                reply_message(reply_token, AREA_OUT_OF_SCOPE_REPLY, sender_token)

                return

            reply_message(reply_token, "笶� 逋ｻ骭ｲ螟ｱ謨�", sender_token)

            return

        active_projects = deduplicate_projects(get_active_projects())

        if not active_projects:

            name = info.get("name", "(no name)")

            skills_str = ", ".join(info.get("skills", [])) or "N/A"

            price = normalize_price(info.get("price", 0))

            reply_message(reply_token,

                f"搭 逋ｻ骭ｲ螳御ｺ�\n蜷榊燕: {name}\n繧ｹ繧ｭ繝ｫ: {skills_str}\n蜊倅ｾ｡: {price}荳Ⅸn\n遞ｼ蜒堺ｸｭ譯井ｻｶ縺ｪ縺�",

                sender_token)

            return

        result_m = run_reverse_matching(info, active_projects)

        matches = result_m.get("matches", [])[:3]

        if MATCHING_LOGIC_AVAILABLE:
            msg = build_reverse_match_message_v2(
                info.get("name", "(no name)"), matches,
                normalize_price(info.get("price", 0)) or 0)
        else:
            msg = build_reverse_match_message(info.get("name", "(no name)"), matches)

        reply_message(reply_token, msg, sender_token)



    elif msg_type == "engineers":

        engineers_list = info.get("engineers", [])

        if not engineers_list:

            reply_message(reply_token, "笶� 莠ｺ蜩｡諠�蝣ｱ縺悟叙蠕励〒縺阪∪縺帙ｓ縺ｧ縺励◆", sender_token)

            return

        success_count = skip_count = 0

        skip_reasons = set()

        registered = []

        for eng in engineers_list:

            ok, reason = register_engineer(eng, text, sender, user_id=user_id)

            if ok:

                success_count += 1

                registered.append(eng)

            else:

                skip_count += 1

                if reason:

                    skip_reasons.add(reason)

        msg = f"投 隍�謨ｰ莠ｺ蜩｡逋ｻ骭ｲ螳御ｺ�\n逋ｻ骭ｲ: {success_count}蜷� / 繧ｹ繧ｭ繝�繝�: {skip_count}蜷構n"

        if "name_not_found" in skip_reasons:

            msg += f"{ENGINEER_NAME_NOT_FOUND_REPLY}\n"

        if "area_out_of_scope" in skip_reasons:

            msg += f"{AREA_OUT_OF_SCOPE_REPLY}\n"

        for i, e in enumerate(engineers_list[:5], 1):

            msg += f"{i}. {e.get('name','(no name)')} / {e.get('price',0)}荳Ⅸn"

        reply_message(reply_token, msg, sender_token)

        active_projects = deduplicate_projects(get_active_projects())

        if active_projects and registered:

            uid = MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID

            tok = MATSUNO_CHANNEL_TOKEN if sender == "matsuno" else OKAMOTO_CHANNEL_TOKEN

            for eng in registered[:3]:

                rm = run_reverse_matching(eng, active_projects)

                matches = rm.get("matches", [])[:3]

                if matches:

                    if MATCHING_LOGIC_AVAILABLE:
                        _rmsg = build_reverse_match_message_v2(
                            eng.get("name","?"), matches,
                            normalize_price(eng.get("price", 0)) or 0)
                    else:
                        _rmsg = build_reverse_match_message(eng.get("name","?"), matches)
                    push_message(uid, _rmsg, tok)



    elif msg_type == "project":

        success, _ = register_project(info, text, sender, user_id=user_id)

        proj_name = info.get("name", "project")

        if not success:

            reply_message(reply_token, "笶� 譯井ｻｶ逋ｻ骭ｲ螟ｱ謨�", sender_token)

            return

        engineers = get_available_engineers()

        matching = run_matching(info, engineers)

        all_candidates = matching.get("candidates", [])

        project_price = normalize_price(info.get("price", 0)) or 0

        proposal_draft = matching.get("proposal_draft", "")



        ok_candidates, ng_candidates = [], []

        for c in all_candidates:

            is_ok, ng_reasons, detail_str = evaluate_candidate(c, project_price)

            if is_ok: ok_candidates.append((c, detail_str))

            else: ng_candidates.append((c, ng_reasons, detail_str))



        PENDING_PROPOSALS[pending_key] = {

            "ok": ok_candidates,

            "ng": ng_candidates,

            "proposal_draft": proposal_draft,

            "proj_name": proj_name,

        }



        msg = build_matching_message(proj_name, ok_candidates, ng_candidates, proposal_draft)

        reply_message(reply_token, msg, sender_token)



    elif msg_type == "projects":

        projects_list = info.get("projects", [])

        if not projects_list:

            reply_message(reply_token, "笶� 譯井ｻｶ諠�蝣ｱ縺悟叙蠕励〒縺阪∪縺帙ｓ縺ｧ縺励◆", sender_token)

            return

        success_count = skip_count = 0

        for proj in projects_list:

            ok, _ = register_project(proj, text, sender, user_id=user_id)

            if ok: success_count += 1

            else: skip_count += 1

        msg = f"投 隍�謨ｰ譯井ｻｶ逋ｻ骭ｲ螳御ｺ�\n逋ｻ骭ｲ: {success_count}莉ｶ / 繧ｹ繧ｭ繝�繝�: {skip_count}莉ｶ\n"

        for i, p in enumerate(projects_list[:5], 1):

            msg += f"{i}. {p.get('name','(no name)')} / {p.get('price',0)}荳Ⅸn"

        reply_message(reply_token, msg, sender_token)



    else:

        print(f"[other] ignored: {text[:50]}")





def handle_webhook(channel_secret, channel_token, sender_name):

    signature = request.headers.get('X-Line-Signature', '')

    body = request.get_data()

    if not verify_signature(body, signature, channel_secret):

        abort(400)

    events = request.json.get('events', [])

    for event in events:

        event_type = event['type']

        if event_type != 'message':

            continue



        msg = event['message']

        msg_type = msg.get('type', '')

        reply_token = event['replyToken']

        user_id = event.get('source', {}).get('userId', '')



        global MATSUNO_USER_ID

        if sender_name == "matsuno" and user_id and not MATSUNO_USER_ID:

            MATSUNO_USER_ID = user_id

            print(f"[userId-matsuno] {user_id}", flush=True)

            if os.path.exists(ENV_PATH):

                set_key(ENV_PATH, "MATSUNO_LINE_USER_ID", user_id)



        try:

            if msg_type == 'text':

                process_message(msg['text'], reply_token, sender_name, channel_token, user_id=user_id)

            elif msg_type in ('image', 'file'):

                # PDF/逕ｻ蜒上せ繧ｭ繝ｫ繧ｷ繝ｼ繝亥女菫｡

                mime = msg.get('contentType', 'image/jpeg') if msg_type == 'image' else msg.get('fileName', '')

                # 繝輔ぃ繧､繝ｫ蜷阪°繧窺IME蛻､螳�

                if msg_type == 'file':

                    fname = msg.get('fileName', '').lower()

                    if fname.endswith('.pdf'):

                        mime = 'application/pdf'

                    elif fname.endswith('.docx'):

                        mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

                    elif fname.endswith(('.png', '.jpg', '.jpeg')):

                        mime = f"image/{'png' if fname.endswith('.png') else 'jpeg'}"

                    else:

                        mime = 'application/octet-stream'

                handle_file_message(msg['id'], mime, reply_token, sender_name, channel_token)

        except Exception as e:

            print(f"Error [{sender_name}]: {e}")

            traceback.print_exc()



    return 'OK', 200





@app.route('/webhook', methods=['POST'])

def webhook_matsuno():

    return handle_webhook(MATSUNO_CHANNEL_SECRET, MATSUNO_CHANNEL_TOKEN, "matsuno")



@app.route('/webhook_okamoto', methods=['POST'])

def webhook_okamoto():

    return handle_webhook(OKAMOTO_CHANNEL_SECRET, OKAMOTO_CHANNEL_TOKEN, "okamoto")



@app.route('/health', methods=['GET'])

def health():

    return 'OK', 200



def _keepalive():

    time.sleep(60)

    url = os.environ.get('RENDER_EXTERNAL_URL', 'https://ses-work-automation.onrender.com')

    while True:

        try:

            requests.get(f'{url}/health', timeout=10)

            print('[keepalive] ping OK')

        except Exception as e:

            print(f'[keepalive] ping failed: {e}')

        time.sleep(600)



threading.Thread(target=_keepalive, daemon=True).start()



if __name__ == '__main__':

    port = int(os.environ.get('PORT', 5000))

    app.run(host='0.0.0.0', port=port)


```

## local_server/command_server.py

```py
"""
繧ｸ繝ｧ繝悶ぜ逕ｨ 繝ｭ繝ｼ繧ｫ繝ｫ繧ｳ繝槭Φ繝牙ｮ溯｡後し繝ｼ繝舌�ｼ
- localhost:8765 縺ｧHTTP繝ｪ繧ｯ繧ｨ繧ｹ繝医ｒ蜿励￠莉倥￠繧�
- 繧ｸ繝ｧ繝悶ぜ�ｼ�Claude�ｼ峨′Filesystem MCP縺ｾ縺溘�ｯHTTP邨檎罰縺ｧ繧ｳ繝槭Φ繝峨ｒ騾∽ｿ｡ 竊� PC荳翫〒螳溯｡� 竊� 邨先棡繧定ｿ斐☆
- 繧ｻ繧ｭ繝･繝ｪ繝�繧｣: localhost縺ｮ縺ｿ蜿嶺ｻ倥√ヨ繝ｼ繧ｯ繝ｳ隱崎ｨｼ縺ゅｊ
- v2: ThreadingHTTPServer蛹厄ｼ磯聞譎る俣繧ｳ繝槭Φ繝峨〒繝悶Ο繝�繧ｯ縺励↑縺��ｼ�
- v2: timeout荳企剞3600遘抵ｼ�1譎る俣�ｼ峨�/write_and_run繧Ｕimeout繧偵Μ繧ｯ繧ｨ繧ｹ繝医°繧牙女縺大叙繧�
"""

import http.server
import json
import subprocess
import os
import sys
import logging
from datetime import datetime
from socketserver import ThreadingMixIn

# ========== 險ｭ螳� ==========
PORT = 8765
AUTH_TOKEN = "jobz-terra-2026"
LOG_FILE = r"C:\Users\ma_py\OneDrive\繝�繧ｹ繧ｯ繝医ャ繝予ses_work\local_server\server.log"
MAX_TIMEOUT = 3600  # 荳企剞1譎る俣
# ==========================

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class ThreadingHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    """蜷�繝ｪ繧ｯ繧ｨ繧ｹ繝医ｒ蛻･繧ｹ繝ｬ繝�繝峨〒蜃ｦ逅�縺吶ｋHTTP繧ｵ繝ｼ繝舌�ｼ縲�
    髟ｷ譎る俣繧ｳ繝槭Φ繝牙ｮ溯｡御ｸｭ繧ゆｻ悶�ｮ繝ｪ繧ｯ繧ｨ繧ｹ繝医ｒ蜿励￠莉倥￠邯壹￠繧九�"""
    daemon_threads = True


class CommandHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def check_auth(self):
        token = self.headers.get("X-Auth-Token", "")
        return token == AUTH_TOKEN

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {
                "status": "ok",
                "server": "jobz-command-server",
                "time": datetime.now().isoformat()
            })
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        # localhost莉･螟悶�ｯ諡貞凄
        if self.client_address[0] not in ("127.0.0.1", "::1"):
            self.send_json(403, {"error": "forbidden: localhost only"})
            return

        # 隱崎ｨｼ繝√ぉ繝�繧ｯ
        if not self.check_auth():
            self.send_json(401, {"error": "unauthorized: invalid token"})
            return

        # 繝懊ョ繧｣隱ｭ縺ｿ霎ｼ縺ｿ
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            req = json.loads(body)
        except json.JSONDecodeError:
            self.send_json(400, {"error": "invalid JSON"})
            return

        path = self.path

        # ========== /run : 繧ｳ繝槭Φ繝牙ｮ溯｡� ==========
        if path == "/run":
            cmd = req.get("cmd", "")
            cwd = req.get("cwd", r"C:\Users\ma_py\OneDrive\繝�繧ｹ繧ｯ繝医ャ繝予ses_work")
            timeout = min(int(req.get("timeout", 60)), MAX_TIMEOUT)

            if not cmd:
                self.send_json(400, {"error": "cmd is required"})
                return

            logger.info(f"[RUN] cmd={cmd} cwd={cwd} timeout={timeout}s")
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                )
                self.send_json(200, {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "cmd": cmd,
                })
            except subprocess.TimeoutExpired:
                self.send_json(408, {"error": f"timeout after {timeout}s", "cmd": cmd})
            except Exception as e:
                self.send_json(500, {"error": str(e), "cmd": cmd})

        # ========== /write_and_run : 繝輔ぃ繧､繝ｫ譖ｸ縺崎ｾｼ縺ｿ 竊� 螳溯｡� ==========
        elif path == "/write_and_run":
            filepath = req.get("filepath", "")
            content = req.get("content", "")
            run_cmd = req.get("run_cmd", "")
            cwd = req.get("cwd", r"C:\Users\ma_py\OneDrive\繝�繧ｹ繧ｯ繝医ャ繝予ses_work")
            timeout = min(int(req.get("timeout", 120)), MAX_TIMEOUT)

            if not filepath or not content:
                self.send_json(400, {"error": "filepath and content are required"})
                return

            try:
                os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"[WRITE] {filepath}")

                result_data = {"filepath": filepath, "written": True}

                if run_cmd:
                    logger.info(f"[RUN after write] {run_cmd} timeout={timeout}s")
                    result = subprocess.run(
                        run_cmd, shell=True, cwd=cwd,
                        capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=timeout,
                    )
                    result_data.update({
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                    })

                self.send_json(200, result_data)
            except subprocess.TimeoutExpired:
                self.send_json(408, {"error": f"timeout after {timeout}s", "cmd": run_cmd})
            except Exception as e:
                self.send_json(500, {"error": str(e)})

        else:
            self.send_json(404, {"error": f"unknown endpoint: {path}"})


def run():
    logger.info(f"繧ｸ繝ｧ繝悶ぜ 繧ｳ繝槭Φ繝峨し繝ｼ繝舌�ｼ v2 襍ｷ蜍� 竊� localhost:{PORT}")
    logger.info(f"ThreadingHTTPServer: 譛牙柑�ｼ井ｸｦ蛻励Μ繧ｯ繧ｨ繧ｹ繝亥ｯｾ蠢懶ｼ�")
    logger.info(f"譛螟ｧtimeout: {MAX_TIMEOUT}遘�")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), CommandHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("繧ｵ繝ｼ繝舌�ｼ蛛懈ｭ｢")
        server.shutdown()


if __name__ == "__main__":
    run()

```

## local_server/mcp_bridge.py

```py
"""
繧ｸ繝ｧ繝悶ぜ逕ｨ 繧ｳ繝槭Φ繝牙ｮ溯｡勲CP繧ｵ繝ｼ繝舌�ｼ
Claude Desktop 縺九ｉ菴ｿ縺医ｋMCP繝�繝ｼ繝ｫ縺ｨ縺励※ command_server.py 縺ｫ讖区ｸ｡縺励☆繧�

險ｭ螳�: claude_desktop_config.json 縺ｫ霑ｽ蜉縺悟ｿ�隕�
"""

import asyncio
import json
import urllib.request
import urllib.error
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

AUTH_TOKEN = "jobz-terra-2026"
SERVER_URL = "http://127.0.0.1:8765"

app = Server("jobz-command-mcp")


def http_post(endpoint: str, payload: dict, timeout: int = 90) -> dict:
    url = f"{SERVER_URL}{endpoint}"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Auth-Token": AUTH_TOKEN,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}"}
    except Exception as e:
        return {"error": str(e)}


@app.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="run_command",
            description="繝ｭ繝ｼ繧ｫ繝ｫPC縺ｧ繧ｿ繝ｼ繝溘リ繝ｫ繧ｳ繝槭Φ繝峨ｒ螳溯｡後☆繧九１ython/bat/pip/git/node遲峨↑繧薙〒繧ょｮ溯｡悟庄閭ｽ縲�",
            inputSchema={
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "螳溯｡後☆繧九さ繝槭Φ繝会ｼ井ｾ�: python script.py, pip install requests, git push�ｼ�"},
                    "cwd": {"type": "string", "description": "螳溯｡後ョ繧｣繝ｬ繧ｯ繝医Μ�ｼ育怐逡･譎ゅ�ｯses_work�ｼ�"},
                    "timeout": {"type": "integer", "description": "繧ｿ繧､繝繧｢繧ｦ繝育ｧ呈焚�ｼ医ョ繝輔か繝ｫ繝�60�ｼ�"},
                },
                "required": ["cmd"],
            },
        ),
        types.Tool(
            name="write_and_run",
            description="繝輔ぃ繧､繝ｫ繧呈嶌縺崎ｾｼ繧薙〒縺九ｉ蜊ｳ螳溯｡後☆繧九ゅせ繧ｯ繝ｪ繝励ヨ菴懈�絶�貞ｮ溯｡後ｒ1繧ｹ繝�繝�繝励〒螳檎ｵ舌�",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "譖ｸ縺崎ｾｼ縺ｿ蜈医�ｮ繝輔Ν繝代せ"},
                    "content": {"type": "string", "description": "繝輔ぃ繧､繝ｫ縺ｮ蜀�螳ｹ"},
                    "run_cmd": {"type": "string", "description": "譖ｸ縺崎ｾｼ縺ｿ蠕後↓螳溯｡後☆繧九さ繝槭Φ繝会ｼ育怐逡･蜿ｯ�ｼ�"},
                    "cwd": {"type": "string", "description": "螳溯｡後ョ繧｣繝ｬ繧ｯ繝医Μ�ｼ育怐逡･譎ゅ�ｯses_work�ｼ�"},
                },
                "required": ["filepath", "content"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "run_command":
        result = http_post("/run", arguments)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        return [types.TextContent(type="text", text=text)]

    elif name == "write_and_run":
        result = http_post("/write_and_run", arguments)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        return [types.TextContent(type="text", text=text)]

    else:
        return [types.TextContent(type="text", text=f"unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

```

## mail_mcp/mail_server.py

```py
#!/usr/bin/env python3
"""
SES Mail MCP Server
Claude Desktop縺九ｉ繝｡繝ｼ繝ｫ騾∽ｿ｡繝ｻ蜿嶺ｿ｡遒ｺ隱阪′縺ｧ縺阪ｋMCP繧ｵ繝ｼ繝舌�ｼ
"""

import json
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import os
from datetime import datetime
import sys
import io

# Windows stdout/stdin繧旦TF-8縺ｫ蠑ｷ蛻ｶ
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

ACCOUNTS = {
    "matsuno": {
        "email": "r-matsuno@terra-ltd.co.jp",
        "password": os.environ.get("MATSUNO_MAIL_PASSWORD", ""),
        "imap_server": "mail65.onamae.ne.jp",
        "imap_port": 993,
        "smtp_server": "mail65.onamae.ne.jp",
        "smtp_port": 465,
    },
    "okamoto": {
        "email": "r-okamoto@terra-ltd.co.jp",
        "password": os.environ.get("OKAMOTO_MAIL_PASSWORD", ""),
        "imap_server": "mail65.onamae.ne.jp",
        "imap_port": 993,
        "smtp_server": "mail65.onamae.ne.jp",
        "smtp_port": 465,
    },
    "sessales": {
        "email": "sessales@terra-ltd.co.jp",
        "password": os.environ.get("SESSALES_MAIL_PASSWORD", ""),
        "imap_server": "mail65.onamae.ne.jp",
        "imap_port": 993,
        "smtp_server": "mail65.onamae.ne.jp",
        "smtp_port": 465,
    }
}

def send_email(account_name: str, to: str, subject: str, body: str) -> dict:
    account = ACCOUNTS.get(account_name)
    if not account:
        return {"success": False, "error": f"繧｢繧ｫ繧ｦ繝ｳ繝� '{account_name}' 縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ"}
    try:
        msg = MIMEMultipart()
        msg["From"] = account["email"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP_SSL(account["smtp_server"], account["smtp_port"]) as server:
            server.login(account["email"], account["password"])
            server.sendmail(account["email"], to, msg.as_string())
        return {
            "success": True,
            "message": f"騾∽ｿ｡螳御ｺ�: {to} 縺ｸ縲鶏subject}縲阪ｒ騾∽ｿ｡縺励∪縺励◆",
            "from": account["email"],
            "to": to,
            "subject": subject,
            "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_recent_emails(account_name: str, limit: int = 10) -> dict:
    account = ACCOUNTS.get(account_name)
    if not account:
        return {"success": False, "error": f"繧｢繧ｫ繧ｦ繝ｳ繝� '{account_name}' 縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ"}
    try:
        mail = imaplib.IMAP4_SSL(account["imap_server"], account["imap_port"])
        mail.login(account["email"], account["password"])
        mail.select("INBOX")
        _, data = mail.search(None, "ALL")
        ids = data[0].split()
        recent_ids = ids[-limit:] if len(ids) >= limit else ids
        recent_ids = list(reversed(recent_ids))
        emails = []
        for msg_id in recent_ids:
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            subject = ""
            raw_subject = msg.get("Subject", "")
            for part, enc in decode_header(raw_subject):
                if isinstance(part, bytes):
                    subject += part.decode(enc or "utf-8", errors="ignore")
                else:
                    subject += part
            sender = msg.get("From", "")
            date = msg.get("Date", "")
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="ignore")[:500]
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")[:500]
            emails.append({
                "id": msg_id.decode(),
                "subject": subject,
                "from": sender,
                "date": date,
                "body_preview": body
            })
        mail.logout()
        return {"success": True, "emails": emails, "count": len(emails)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_request(request: dict) -> dict:
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ses-mail-mcp", "version": "1.0.0"}
            }
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "tools": [
                    {
                        "name": "send_email",
                        "description": "繝｡繝ｼ繝ｫ繧帝∽ｿ｡縺吶ｋ縲よ收驥弱∪縺溘�ｯ蟯｡譛ｬ縺ｮ繧｢繧ｫ繧ｦ繝ｳ繝医°繧蛾∽ｿ｡蜿ｯ閭ｽ縲�",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "account": {"type": "string", "description": "'matsuno'(譚ｾ驥弱い繝峨Ξ繧ｹ) / 'okamoto'(蟯｡譛ｬ繧｢繝峨Ξ繧ｹ) / 'sessales'(TERRA蜈ｱ騾�)"},
                                "to": {"type": "string", "description": "騾∽ｿ｡蜈医Γ繝ｼ繝ｫ繧｢繝峨Ξ繧ｹ"},
                                "subject": {"type": "string", "description": "莉ｶ蜷�"},
                                "body": {"type": "string", "description": "譛ｬ譁�"}
                            },
                            "required": ["account", "to", "subject", "body"]
                        }
                    },
                    {
                        "name": "get_recent_emails",
                        "description": "譛譁ｰ縺ｮ繝｡繝ｼ繝ｫ荳隕ｧ繧貞叙蠕励☆繧�",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "account": {"type": "string", "description": "'matsuno'(譚ｾ驥弱い繝峨Ξ繧ｹ) / 'okamoto'(蟯｡譛ｬ繧｢繝峨Ξ繧ｹ) / 'sessales'(TERRA蜈ｱ騾�)"},
                                "limit": {"type": "integer", "description": "蜿門ｾ嶺ｻｶ謨ｰ�ｼ医ョ繝輔か繝ｫ繝�10�ｼ�", "default": 10}
                            },
                            "required": ["account"]
                        }
                    }
                ]
            }
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})
        if tool_name == "send_email":
            result = send_email(args["account"], args["to"], args["subject"], args["body"])
        elif tool_name == "get_recent_emails":
            result = get_recent_emails(args["account"], args.get("limit", 10))
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=True, indent=2)}]
            }
        }

    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    }


def main():
    # stderr縺ｫ繝ｭ繧ｰ蜃ｺ蜉幢ｼ医ョ繝舌ャ繧ｰ逕ｨ�ｼ�
    sys.stderr.write("ses-mail-mcp: starting...\n")
    sys.stderr.flush()
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            
            request = json.loads(line)
            method = request.get("method", "")
            req_id = request.get("id")
            
            # 騾夂衍繝｡繝�繧ｻ繝ｼ繧ｸ�ｼ�id縺ｪ縺暦ｼ峨�ｯ蠢懃ｭ比ｸ崎ｦ�
            if req_id is None:
                sys.stderr.write(f"ses-mail-mcp: notification received: {method}\n")
                sys.stderr.flush()
                continue
            
            response = handle_request(request)
            out = json.dumps(response, ensure_ascii=True)
            sys.stdout.write(out + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            continue
        except Exception as e:
            sys.stderr.write(f"ses-mail-mcp: error: {e}\n")
            sys.stderr.flush()
            if 'req_id' in dir() and req_id is not None:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32700, "message": str(e)}
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    main()

```

## freee/freee_invoice_v2.py

```py
"""
freee_invoice_v2.py
螂醍ｴ�繝槭せ繧ｿ繝ｼExcel繧呈ｭ｣縺ｨ縺励※遞ｼ蜒堺ｸｭ莠ｺ蜩｡縺ｮ隲区ｱよ嶌繧断reee縺ｫ繝峨Λ繝輔ヨ菴懈�舌�

隲区ｱゅΝ繝ｼ繝ｫ:
縲慎ERRA縲�
  P�ｼ医�励Ο繝代�ｼ�ｼ�: GL/FP邨檎罰莉･螟� 竊� 15,000蜀�/莠ｺ�ｼ育ｨ主挨�ｼ牙崋螳�
  P�ｼ医�励Ο繝代�ｼ�ｼ�: GL/FP邨檎罰遞ｼ蜒� 竊� 隲区ｱゅ↑縺�
  BP: 邊怜茜ﾃ�80%
  TERRA謚伜濠: 邊怜茜ﾃ�50%
  蟯｡譛ｬ謚伜濠: 邊怜茜ﾃ�80%
縲舌ヵ繝ｩ繝�繝励ユ繝�繧ｯ縲�
  騾壼ｸｸ: 邊怜茜ﾃ�68%
  蟆丞揩謚伜濠: 邊怜茜ﾃ�48%
  蟯｡譛ｬ謚伜濠: 邊怜茜ﾃ�68%
  蟯｡譛ｬ: 邊怜茜ﾃ�68%蜈ｨ鬘肴鴛蜃ｺ
縲舌げ繝ｬ繧､繧ｹ繝ｩ繧､繝ｳ縲�
  邊怜茜ﾃ�60%
"""

import os, sys, requests
from datetime import date
from dateutil.relativedelta import relativedelta
import openpyxl

# token_manager繧貞盾辣ｧ�ｼ郁�ｪ蜍輔Μ繝輔Ξ繝�繧ｷ繝･莉倥″�ｼ�
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\繝�繧ｹ繧ｯ繝医ャ繝予ses_work\freee_auth")
from token_manager import get_headers

# ===== 險ｭ螳� =====
EXCEL_PATH = r"C:\Users\ma_py\OneDrive\繝�繧ｹ繧ｯ繝医ャ繝予ses_work\contract\螂醍ｴ�繝槭せ繧ｿ繝ｼ_v6.xlsx"
FREEE_BASE = "https://api.freee.co.jp/api/1"
COMPANY_ID = 11712776

def freee_headers():
    h = get_headers()
    h["Content-Type"] = "application/json"
    return h

def safe_int(v):
    """蛟､繧貞ｮ牙�ｨ縺ｫint縺ｫ螟画鋤縲よ枚蟄怜�励ｄ譌･莉伜梛縺ｯ繧ｹ繧ｭ繝�繝�(0霑泌唆)"""
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    # 譁�蟄怜�励�ｻ譌･莉伜梛縺ｯ繧ｹ繧ｭ繝�繝�
    return 0

def is_valid_name(v):
    """豌丞錐縺ｨ縺励※譛牙柑縺九メ繧ｧ繝�繧ｯ縲よ律莉伜梛繝ｻ謨ｰ蛟､繝ｻ遨ｺ縺ｯ髯､螟�"""
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return False
    import datetime
    if isinstance(v, (datetime.datetime, datetime.date)):
        return False
    s = str(v).strip()
    if not s or s in ("NaN", "遞ｼ蜒堺ｸｭ蜷郁ｨ�"):
        return False
    # 謨ｰ蟄励□縺代�ｮ譁�蟄怜�励ｂ髯､螟�
    if s.replace("/", "").replace("-", "").isdigit():
        return False
    return True

# ===== Excel隱ｭ縺ｿ霎ｼ縺ｿ =====
def load_active_entries():
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    entries = []

    # --- TERRA ---
    # 繝倥ャ繝繝ｼ: 諡�蠖�(0) 蛹ｺ蛻�(1) 繧ｹ繝�繝ｼ繧ｿ繧ｹ(2) 豌丞錐(3) ... 譯井ｻｶ/荳贋ｽ堺ｼ夂､ｾ(6) 蜊倅ｾ｡(譯井ｻｶ)(7) ... 莉募�･蜊倅ｾ｡(12)
    ws = wb["TERRA"]
    rows = list(ws.iter_rows(values_only=True))
    header_row = None
    for i, row in enumerate(rows):
        if row and "諡�蠖�" in str(row[0]):
            header_row = i
            break
    if header_row is not None:
        for row in rows[header_row+1:]:
            if not any(row): continue
            tantou   = str(row[0] or "").strip()
            kubun    = str(row[1] or "").strip()
            status   = str(row[2] or "").strip()
            name     = row[3]
            case     = str(row[6] or "").strip()
            tanka    = safe_int(row[7])
            shiire   = safe_int(row[12])

            if "遞ｼ蜒堺ｸｭ" not in status: continue
            if not is_valid_name(name): continue
            name = str(name).strip()

            is_gl_ft = any(k in case for k in ["繧ｰ繝ｬ繧､繧ｹ繝ｩ繧､繝ｳ", "繝輔Λ繝�繝励ユ繝�繧ｯ", "GL", "FT"])
            profit = tanka - shiire

            if kubun == "P":
                if is_gl_ft:
                    continue  # 隲区ｱゅ↑縺�
                seikyu = 15000
                rule   = "繝励Ο繝代�ｼ竊�15,000蜀�蝗ｺ螳�"
            elif kubun == "BP":
                if tantou == "TERRA謚伜濠":
                    seikyu = int(profit * 0.50)
                    rule   = "TERRA謚伜濠竊堤ｲ怜茜ﾃ�50%"
                elif tantou == "蟯｡譛ｬ謚伜濠":
                    seikyu = int(profit * 0.80)
                    rule   = "蟯｡譛ｬ謚伜濠竊堤ｲ怜茜ﾃ�80%�ｼ亥ｲ｡譛ｬ謇募�ｺ縺ゅｊ�ｼ�"
                else:
                    seikyu = int(profit * 0.80)
                    rule   = "BP竊堤ｲ怜茜ﾃ�80%"
            else:
                seikyu = 15000
                rule   = "荳肴�寂��15,000蜀�蝗ｺ螳�"

            if seikyu <= 0: continue

            entries.append({
                "partner": "譬ｪ蠑丈ｼ夂､ｾTERRA",
                "name": name, "profit": profit, "seikyu": seikyu,
                "rule": rule, "source": "TERRA"
            })

    # --- 繝輔Λ繝�繝励ユ繝�繧ｯ ---
    # 繝倥ャ繝繝ｼ: 諡�蠖�(0) 繧ｹ繝�繝ｼ繧ｿ繧ｹ(1) 豌丞錐(2) 蜿ら判譎よ悄(3) 譛滄俣(4) 譯井ｻｶ/荳贋ｽ�(5) 譯井ｻｶ蜊倅ｾ｡(6) 莉募�･蜊倅ｾ｡(7)
    ws = wb["繝輔Λ繝�繝励ユ繝�繧ｯ"]
    rows = list(ws.iter_rows(values_only=True))
    header_row = None
    for i, row in enumerate(rows):
        if row and "諡�蠖�" in str(row[0]) and "繧ｹ繝�繝ｼ繧ｿ繧ｹ" in str(row[1] or ""):
            header_row = i
            break
    if header_row is not None:
        for row in rows[header_row+1:]:
            if not any(row): continue
            tantou  = str(row[0] or "").strip()
            status  = str(row[1] or "").strip()
            name    = row[2]
            tanka   = safe_int(row[6])   # 譯井ｻｶ蜊倅ｾ｡(荳贋ｽ阪°繧�)
            shiire  = safe_int(row[7])   # 莉募�･蜊倅ｾ｡(荳倶ｽ阪∈)

            if "遞ｼ蜒堺ｸｭ" not in status: continue
            if not is_valid_name(name): continue
            name = str(name).strip()
            if tanka == 0: continue  # 蜊倅ｾ｡譛ｪ蜈･蜉帙�ｯ繧ｹ繧ｭ繝�繝�

            profit = tanka - shiire

            if profit <= 0:
                print(f"  [SKIP] {name}: 邊怜茜{profit:,}蜀��ｼ亥腰萓｡={tanka:,} 莉募�･={shiire:,}�ｼ�")
                continue

            if tantou == "蟆丞揩謚伜濠":
                seikyu = int(profit * 0.48)
                rule   = "蟆丞揩謚伜濠竊堤ｲ怜茜ﾃ�48%"
            elif tantou in ("蟯｡譛ｬ謚伜濠", "蟯｡譛ｬ"):
                seikyu = int(profit * 0.68)
                rule   = f"{tantou}竊堤ｲ怜茜ﾃ�68%�ｼ亥ｲ｡譛ｬ謇募�ｺ縺ゅｊ�ｼ�"
            else:
                seikyu = int(profit * 0.68)
                rule   = "騾壼ｸｸ竊堤ｲ怜茜ﾃ�68%"

            if seikyu <= 0: continue

            entries.append({
                "partner": "譬ｪ蠑丈ｼ夂､ｾ繝輔Λ繝�繝励ユ繝�繧ｯ",
                "name": name, "profit": profit, "seikyu": seikyu,
                "rule": rule, "source": "FT"
            })

    # --- 繧ｰ繝ｬ繧､繧ｹ繝ｩ繧､繝ｳ ---
    # 繝倥ャ繝繝ｼ: 繧ｹ繝�繝ｼ繧ｿ繧ｹ(0) 豌丞錐(1) 蜿ら判譎よ悄(2) 譛滄俣(3) 譯井ｻｶ/荳贋ｽ�(4) 譯井ｻｶ蜊倅ｾ｡(5) 莉募�･蜊倅ｾ｡(6)
    ws = wb["繧ｰ繝ｬ繧､繧ｹ繝ｩ繧､繝ｳ"]
    rows = list(ws.iter_rows(values_only=True))
    header_row = None
    for i, row in enumerate(rows):
        if row and "繧ｹ繝�繝ｼ繧ｿ繧ｹ" in str(row[0]):
            header_row = i
            break
    if header_row is not None:
        for row in rows[header_row+1:]:
            if not any(row): continue
            status  = str(row[0] or "").strip()
            name    = row[1]
            tanka   = safe_int(row[5])   # 譯井ｻｶ蜊倅ｾ｡(荳贋ｽ阪°繧�)
            shiire  = safe_int(row[6])   # 莉募�･蜊倅ｾ｡(荳倶ｽ阪∈)

            if "遞ｼ蜒堺ｸｭ" not in status: continue
            if not is_valid_name(name): continue
            name = str(name).strip()
            if tanka == 0: continue

            profit = tanka - shiire

            if profit <= 0:
                print(f"  [SKIP] {name}: 邊怜茜{profit:,}蜀��ｼ亥腰萓｡={tanka:,} 莉募�･={shiire:,}�ｼ�")
                continue

            seikyu = int(profit * 0.60)
            if seikyu <= 0: continue

            entries.append({
                "partner": "繧ｰ繝ｬ繧､繧ｹ繝ｩ繧､繝ｳ譬ｪ蠑丈ｼ夂､ｾ",
                "name": name, "profit": profit, "seikyu": seikyu,
                "rule": "GL竊堤ｲ怜茜ﾃ�60%", "source": "GL"
            })

    return entries

# ===== freee: 蜿門ｼ募�亥叙蠕�/菴懈�� =====
def get_or_create_partner(name):
    res = requests.get(f"{FREEE_BASE}/partners",
        headers=freee_headers(),
        params={"company_id": COMPANY_ID, "keyword": name})
    partners = res.json().get("partners", [])
    if partners: return partners[0]["id"]
    res2 = requests.post(f"{FREEE_BASE}/partners",
        headers=freee_headers(),
        json={"company_id": COMPANY_ID, "name": name, "partner_type": "customer"})
    return res2.json()["partner"]["id"]

# ===== freee: 隲区ｱよ嶌繝峨Λ繝輔ヨ菴懈�� =====
def create_invoice(entry, issue_date, due_date):
    partner_id = get_or_create_partner(entry["partner"])
    mon = f"{issue_date.year}蟷ｴ{issue_date.month}譛�"
    payload = {
        "company_id": COMPANY_ID,
        "issue_date":  issue_date.strftime("%Y-%m-%d"),
        "due_date":    due_date.strftime("%Y-%m-%d"),
        "partner_id":  partner_id,
        "invoice_status": "draft",
        "title": f"{mon}蛻� 讌ｭ蜍吝ｧ碑ｨ玲侭�ｼ�{entry['name']}讒假ｼ�",
        "description": f"[{entry['rule']}] 邊怜茜: {entry['profit']:,}蜀�",
        "invoice_lines": [{
            "name":       f"讌ｭ蜍吝ｧ碑ｨ玲侭�ｼ�{entry['name']}讒假ｼ閲mon}蛻�",
            "quantity":   1,
            "unit_price": entry["seikyu"],
            "tax_code":   1,
            "type":       "normal"
        }]
    }
    res = requests.post(f"{FREEE_BASE}/invoices", headers=freee_headers(), json=payload)
    if res.status_code in (200, 201):
        inv_id = res.json()["invoice"]["id"]
        print(f"  OK {entry['name']} / {entry['partner']} / {entry['seikyu']:,}蜀� [{entry['rule']}] -> ID:{inv_id}")
        return True
    else:
        print(f"  NG {entry['name']} / {res.status_code}: {res.text[:200]}")
        return False

# ===== 繝｡繧､繝ｳ =====
def run(target_month=None):
    today = date.today()
    if target_month is None:
        target_month = (today.replace(day=1) + relativedelta(months=1))
    issue_date = target_month.replace(day=1)
    due_date   = issue_date + relativedelta(months=1) - relativedelta(days=1)

    print(f"=== freee隲区ｱよ嶌閾ｪ蜍慕函謌� v2 ===")
    print(f"隲区ｱょｯｾ雎｡譛�: {target_month.year}蟷ｴ{target_month.month}譛亥��")
    print(f"隲区ｱよ律: {issue_date}  謾ｯ謇墓悄髯�: {due_date}")
    print()

    entries = load_active_entries()
    print(f"蟇ｾ雎｡莠ｺ蜩｡: {len(entries)}蜷�")
    for e in entries:
        print(f"  {e['source']} | {e['name']} | 邊怜茜{e['profit']:,}蜀� | 隲区ｱ�{e['seikyu']:,}蜀� | {e['rule']}")
    print()

    ok = ng = 0
    for e in entries:
        if create_invoice(e, issue_date, due_date): ok += 1
        else: ng += 1

    print()
    print(f"=== 螳御ｺ�: 菴懈�須ok}莉ｶ / 繧ｨ繝ｩ繝ｼ{ng}莉ｶ ===")
    print(f"-> https://secure.freee.co.jp/invoices")
    # ===== 隲区ｱよ嶌菴懈�仙ｮ御ｺ�蠕�: 螂醍ｴ�繝槭せ繧ｿ繝ｼ縺ｮ繧ｹ繝�繝ｼ繧ｿ繧ｹ繧定�ｪ蜍墓峩譁ｰ =====
    if ok > 0:
        try:
            import sys as _sys2
            import os as _os2
            _sys2.path.insert(0, _os2.path.dirname(__file__))
            from auto_status_update import update_status_after_invoice
            invoiced_names = [e["name"] for e in entries]
            print(f"\n[auto_status] 隲区ｱよ嶌菴懈�先ｸ医∩莠ｺ蜩｡縺ｮ繧ｹ繝�繝ｼ繧ｿ繧ｹ繧堤ｨｼ蜒堺ｸｭ縺ｫ譖ｴ譁ｰ...")
            update_status_after_invoice(names=invoiced_names)
        except Exception as _e:
            print(f"[auto_status] 繧ｹ繝�繝ｼ繧ｿ繧ｹ譖ｴ譁ｰ繧ｹ繧ｭ繝�繝暦ｼ医お繝ｩ繝ｼ: {_e}�ｼ�")

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1:
        y, m = map(int, _sys.argv[1].split("-"))
        run(date(y, m, 1))
    else:
        run()

```

## freee_auth/token_manager.py

```py
"""
freee 繝医�ｼ繧ｯ繝ｳ邂｡逅�繝｢繧ｸ繝･繝ｼ繝ｫ
- access_token縺ｯ6譎る俣縺ｧ譛滄剞蛻�繧� 竊� refresh_token縺ｧ閾ｪ蜍墓峩譁ｰ
- 縺薙�ｮ繝｢繧ｸ繝･繝ｼ繝ｫ繧段mport縺吶ｋ縺縺代〒繝医�ｼ繧ｯ繝ｳ邂｡逅�縺悟ｮ檎ｵ�
"""
import json, time, requests, os

CLIENT_ID     = "731109064351970"
CLIENT_SECRET = "***MASKED***"
TOKEN_FILE    = r"C:\Users\ma_py\OneDrive\繝�繧ｹ繧ｯ繝医ャ繝予ses_work\freee_auth\freee_token.json"
COMPANY_ID    = 11712776

def load_token():
    with open(TOKEN_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_token(data):
    data["saved_at"] = int(time.time())
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def refresh_access_token():
    token_data = load_token()
    res = requests.post(
        "https://accounts.secure.freee.co.jp/public_api/token",
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": token_data["refresh_token"],
        }
    )
    if res.status_code == 200:
        new_data = res.json()
        save_token(new_data)
        print("[TOKEN] 繝ｪ繝輔Ξ繝�繧ｷ繝･謌仙粥")
        return new_data["access_token"]
    else:
        raise Exception(f"Token refresh failed: {res.text}")

def get_access_token():
    """譛牙柑縺ｪaccess_token繧定ｿ斐☆�ｼ域悄髯仙��繧後↑繧芽�ｪ蜍輔Μ繝輔Ξ繝�繧ｷ繝･�ｼ�"""
    token_data = load_token()
    saved_at = token_data.get("saved_at", 0)
    expires_in = token_data.get("expires_in", 21600)
    elapsed = int(time.time()) - saved_at
    
    if elapsed > (expires_in - 300):  # 5蛻�蜑阪↓繝ｪ繝輔Ξ繝�繧ｷ繝･
        print(f"[TOKEN] 譛滄剞蛻�繧�({elapsed}遘堤ｵ碁℃) 竊� 繝ｪ繝輔Ξ繝�繧ｷ繝･")
        return refresh_access_token()
    
    return token_data["access_token"]

def get_headers():
    return {"Authorization": f"Bearer {get_access_token()}"}

if __name__ == "__main__":
    # 繝�繧ｹ繝亥ｮ溯｡�
    token = get_access_token()
    print(f"[OK] access_token蜿門ｾ�: {token[:20]}...")
    
    # API繝�繧ｹ繝�
    res = requests.get(
        f"https://api.freee.co.jp/api/1/companies",
        headers=get_headers()
    )
    print(f"[OK] API謗･邯�: {res.status_code}")
    for c in res.json().get("companies", []):
        print(f"     莠区･ｭ謇: {c.get('display_name')} (ID: {c.get('id')})")

```

## outreach_system/collect_targets.py

```py
import argparse
import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
TARGETS_CSV = BASE_DIR / "targets.csv"
COLLECT_LOG_JSON = BASE_DIR / "collect_log.json"

USER_AGENT = "Mozilla/5.0"
REQUEST_TIMEOUT = 15
REQUEST_SLEEP_SECONDS = 1

QUERIES = [
    "SES莨∵･ｭ 譚ｱ莠ｬ 繝｡繝ｼ繝ｫ繧｢繝峨Ξ繧ｹ site:*.co.jp",
    "SIer 譚ｱ莠ｬ 謗｡逕ｨ contact site:*.co.jp",
    "繧ｷ繧ｹ繝�繝髢狗匱 蜿苓ｨ� 譚ｱ莠ｬ 蝠上＞蜷医ｏ縺� site:*.co.jp",
    "SES豢ｾ驕｣ IT莨∵･ｭ 髢｢譚ｱ mail",
    "繝輔Μ繝ｼ繝ｩ繝ｳ繧ｹ繧ｨ繝ｳ繧ｸ繝九い 邏ｹ莉� SES 譚ｱ莠ｬ",
]
FALLBACK_DOMAINS = {
    "SES莨∵･ｭ 譚ｱ莠ｬ 繝｡繝ｼ繝ｫ繧｢繝峨Ξ繧ｹ site:*.co.jp": [
        "https://www.techbrain.co.jp",
        "https://www.mst-inc.co.jp",
        "https://www.brainets.co.jp",
    ],
    "SIer 譚ｱ莠ｬ 謗｡逕ｨ contact site:*.co.jp": [
        "https://www.nsw.co.jp",
        "https://www.tis.co.jp",
    ],
    "繧ｷ繧ｹ繝�繝髢狗匱 蜿苓ｨ� 譚ｱ莠ｬ 蝠上＞蜷医ｏ縺� site:*.co.jp": [
        "https://www.nttdata.co.jp",
        "https://www.hitachi-solutions.co.jp",
    ],
    "SES豢ｾ驕｣ IT莨∵･ｭ 髢｢譚ｱ mail": [
        "https://www.isg.co.jp",
        "https://www.fsi.co.jp",
    ],
    "繝輔Μ繝ｼ繝ｩ繝ｳ繧ｹ繧ｨ繝ｳ繧ｸ繝九い 邏ｹ莉� SES 譚ｱ莠ｬ": [
        "https://www.techbrain.co.jp",
        "https://www.brainets.co.jp",
    ],
}
KNOWN_COMPANY_NAMES = {
    "www.techbrain.co.jp": "繝�繝�繧ｯ繝悶Ξ繝ｼ繝ｳ譬ｪ蠑丈ｼ夂､ｾ",
    "www.mst-inc.co.jp": "繧ｨ繝繝ｻ繧ｨ繧ｹ繝ｻ繝�繧｣繝ｼ譬ｪ蠑丈ｼ夂､ｾ",
    "www.brainets.co.jp": "譬ｪ蠑丈ｼ夂､ｾ繝悶Ξ繧､繝ｳ繧ｺ",
    "www.isg.co.jp": "譬ｪ蠑丈ｼ夂､ｾISG",
    "www.fsi.co.jp": "蟇悟｣ｫ繧ｽ繝輔ヨ譬ｪ蠑丈ｼ夂､ｾ",
    "www.nsw.co.jp": "NSW譬ｪ蠑丈ｼ夂､ｾ",
    "www.tis.co.jp": "TIS譬ｪ蠑丈ｼ夂､ｾ",
    "www.nttdata.co.jp": "譬ｪ蠑丈ｼ夂､ｾNTT繝�繝ｼ繧ｿ",
    "www.hitachi-solutions.co.jp": "譬ｪ蠑丈ｼ夂､ｾ譌･遶九た繝ｪ繝･繝ｼ繧ｷ繝ｧ繝ｳ繧ｺ",
}

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
CSV_COLUMNS = ["company", "contact_name", "email", "type", "memo"]
PERSONAL_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.co.jp",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "icloud.com",
    "me.com",
    "aol.com",
    "example.com",
    "example.jp",
    "example.co.jp",
    "test.com",
    "test.co.jp",
}
INVALID_EMAIL_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")
SKIP_URL_HOSTS = {
    "google.co.jp",
    "www.google.co.jp",
    "google.com",
    "www.google.com",
    "webcache.googleusercontent.com",
}


def sleep_after_request() -> None:
    time.sleep(REQUEST_SLEEP_SECONDS)


def fetch_url(session: requests.Session, url: str) -> Optional[str]:
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        sleep_after_request()
        response.raise_for_status()
        if not response.encoding or response.encoding.lower() == "iso-8859-1":
            response.encoding = response.apparent_encoding
        return response.text
    except requests.RequestException as exc:
        print(f"蜿門ｾ励お繝ｩ繝ｼ: {url} ({exc})")
        return None


def normalize_site_url(url: str) -> Optional[str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    host = parsed.netloc.lower()
    if host in SKIP_URL_HOSTS or host.endswith(".google.co.jp") or host.endswith(".google.com"):
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def extract_google_result_url(href: str) -> Optional[str]:
    if href.startswith("/url?"):
        query = parse_qs(urlparse(href).query)
        return query.get("q", [None])[0]
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return None


def google_search_domains(session: requests.Session, query: str, limit: int = 5) -> List[str]:
    search_url = f"https://www.google.co.jp/search?q={quote_plus(query)}&num=10&hl=ja"
    html = fetch_url(session, search_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    domains: List[str] = []
    seen: Set[str] = set()
    for link in soup.select("a[href]"):
        result_url = extract_google_result_url(link.get("href", ""))
        if not result_url:
            continue
        site_url = normalize_site_url(result_url)
        if not site_url or site_url in seen:
            continue
        seen.add(site_url)
        domains.append(site_url)
        if len(domains) >= limit:
            break
    if domains:
        return domains

    fallback_domains = FALLBACK_DOMAINS.get(query, [])
    print(f"Google讀懃ｴ｢邨先棡繧呈歓蜃ｺ縺ｧ縺阪↑縺�縺溘ａ繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ蛟呵｣懊ｒ菴ｿ逕ｨ: {query}")
    return fallback_domains[:limit]


def candidate_pages(site_url: str) -> Iterable[str]:
    parsed = urlparse(site_url)
    root = f"{parsed.scheme}://{parsed.netloc}/"
    yield root
    yield urljoin(root, "contact")
    yield urljoin(root, "contact/")
    yield urljoin(root, "contact.html")
    yield urljoin(root, "inquiry")
    yield urljoin(root, "inquiry/")
    yield urljoin(root, "inquiry.php")


def extract_emails(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    text_parts = [soup.get_text(" ", strip=True)]
    for link in soup.select("a[href^='mailto:']"):
        text_parts.append(link.get("href", "").replace("mailto:", ""))
    text = "\n".join(text_parts)

    emails: List[str] = []
    seen: Set[str] = set()
    for email in EMAIL_RE.findall(text):
        cleaned = email.strip().rstrip(".").lower()
        domain = cleaned.split("@")[-1]
        if domain in PERSONAL_EMAIL_DOMAINS or cleaned in seen or cleaned.endswith(INVALID_EMAIL_SUFFIXES):
            continue
        seen.add(cleaned)
        emails.append(cleaned)
    return emails


def extract_company_name(html: str, site_url: str) -> str:
    known_name = KNOWN_COMPANY_NAMES.get(urlparse(site_url).netloc.lower())
    if known_name:
        return known_name

    soup = BeautifulSoup(html, "html.parser")
    og_site_name = soup.find("meta", property="og:site_name")
    if og_site_name and og_site_name.get("content"):
        return normalize_company_name(og_site_name["content"])

    if soup.title and soup.title.string:
        return normalize_company_name(soup.title.string)

    host = urlparse(site_url).netloc
    return host.removeprefix("www.")


def normalize_company_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    for separator in ["�ｽ�", "|", " - ", " 窶� ", " 窶� ", "�ｼ�", "/"]:
        if separator in cleaned:
            cleaned = cleaned.split(separator)[0].strip()
    return cleaned


def judge_company_type(site_url: str, html: str) -> str:
    text = f"{site_url}\n{BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)}"
    if any(keyword in text for keyword in ["SES", "ses", "豢ｾ驕｣", "謚陦楢�豢ｾ驕｣"]):
        return "ses"
    return "prime"


def load_existing_companies(csv_path: Path) -> Set[str]:
    if not csv_path.exists():
        return set()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return {row.get("company", "").strip() for row in reader if row.get("company", "").strip()}


def collect_targets() -> Dict[str, object]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    existing_companies = load_existing_companies(TARGETS_CSV)
    collected: List[Dict[str, str]] = []
    skipped_duplicates = 0
    seen_companies = set(existing_companies)
    visited_sites: Set[str] = set()
    query_logs: List[Dict[str, object]] = []

    for query in QUERIES:
        domains = google_search_domains(session, query)
        query_logs.append({"query": query, "domains": domains})
        for site_url in domains:
            if site_url in visited_sites:
                continue
            visited_sites.add(site_url)

            for page_url in candidate_pages(site_url):
                html = fetch_url(session, page_url)
                if not html:
                    continue
                emails = extract_emails(html)
                if not emails:
                    continue

                company = extract_company_name(html, site_url)
                if company in seen_companies:
                    skipped_duplicates += 1
                    break

                row = {
                    "company": company,
                    "contact_name": "",
                    "email": emails[0],
                    "type": judge_company_type(site_url, html),
                    "memo": page_url,
                }
                collected.append(row)
                seen_companies.add(company)
                break

    return {
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "queries": query_logs,
        "candidates": collected,
        "added_count": len(collected),
        "skipped_duplicate_count": skipped_duplicates,
    }


def append_targets(rows: List[Dict[str, str]], csv_path: Path) -> None:
    file_exists = csv_path.exists()
    with csv_path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        if not file_exists or csv_path.stat().st_size == 0:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_collect_log(result: Dict[str, object]) -> None:
    with COLLECT_LOG_JSON.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)


def print_preview(rows: List[Dict[str, str]]) -> None:
    for row in rows:
        print(f"{row['company']} / {row['email']} / {row['type']} / {row['memo']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="IT繝ｻSES莨∵･ｭ縺ｮ騾｣邨｡蜈医ｒ蜿朱寔縺励※targets.csv縺ｸ霑ｽ險倥＠縺ｾ縺吶�")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="蜿朱寔邨先棡繧定｡ｨ遉ｺ縺励，SV縺ｫ縺ｯ譖ｸ縺崎ｾｼ縺ｿ縺ｾ縺帙ｓ縲�")
    mode.add_argument("--run", action="store_true", help="蜿朱寔邨先棡繧稚argets.csv縺ｸ霑ｽ險倥＠縺ｾ縺吶�")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = collect_targets()
    candidates = result["candidates"]

    if args.dry_run:
        print_preview(candidates)
    else:
        append_targets(candidates, TARGETS_CSV)

    write_collect_log(result)
    print(f"霑ｽ蜉{result['added_count']}遉ｾ / 繧ｹ繧ｭ繝�繝養result['skipped_duplicate_count']}遉ｾ�ｼ磯㍾隍��ｼ�")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

## run_matching_and_notify.bat

```bat
@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
set "LOG_PATH=logs\matching_daily.log"
echo [%date% %time%] 繝槭ャ繝√Φ繧ｰ髢句ｧ� >> "%LOG_PATH%"
python matching_v2\matching_v2.py >> "%LOG_PATH%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] 繝槭ャ繝√Φ繧ｰ螳御ｺ� >> "%LOG_PATH%"
) else (
    echo [%date% %time%] 繝槭ャ繝√Φ繧ｰ螟ｱ謨� >> "%LOG_PATH%"
)
echo [%date% %time%] 螳御ｺ� >> "%LOG_PATH%"

```

## AGENTS.md

```md
# AGENTS.md - Codex謖�遉ｺ譖ｸ
譛邨よ峩譁ｰ: 2026-05-21

## 蠖ｹ蜑ｲ
縺ゅ↑縺溘�ｯ繧ｨ繝ｳ繧ｸ繝九い諡�蠖薙〒縺吶ゅず繝ｧ繝悶ぜ�ｼ�Claude Desktop�ｼ峨°繧�
繧ｿ繧ｹ繧ｯ繧貞女縺大叙繧翫√さ繝ｼ繝峨ｒ螳溯｣�縺励※蝣ｱ蜻翫＠縺ｾ縺吶�

## 諡�蠖馴伜沺

### 繧�繧九％縺ｨ
- Python繧ｹ繧ｯ繝ｪ繝励ヨ譁ｰ隕丈ｽ懈�舌�ｻ菫ｮ豁｣繝ｻ繝舌げ菫ｮ豁｣
- HTML/CSS/JS繝ｻPlaywright閾ｪ蜍募喧繧ｹ繧ｯ繝ｪ繝励ヨ
- 繝舌ャ繝∝�ｦ逅�繝ｻ繝輔ぃ繧､繝ｫ螟画鋤繝ｻ繝�繧ｹ繝亥ｮ溯｡�
- 繧ｸ繝ｧ繝悶ぜ縺梧嶌縺�縺溯ｨｭ險医�ｻ莉墓ｧ倥�ｮ繧ｳ繝ｼ繝牙喧

### 繧�繧峨↑縺�縺薙→
- Notion DB縺ｸ縺ｮ逶ｴ謗･譖ｸ縺崎ｾｼ縺ｿ�ｼ医ず繝ｧ繝悶ぜ縺瑚｡後≧�ｼ�
- 繝｡繝ｼ繝ｫ騾∽ｿ｡縺ｮ蛻､譁ｭ繝ｻ螳溯｡鯉ｼ医ず繝ｧ繝悶ぜ縺瑚｡後≧�ｼ�
- 莠区･ｭ蛻､譁ｭ繝ｻ蜆ｪ蜈磯�菴堺ｻ倥￠

## 菴懈･ｭ繝ｫ繝ｼ繝ｫ
- 菴懈･ｭ繝�繧｣繝ｬ繧ｯ繝医Μ: C:\Users\ma_py\OneDrive\繝�繧ｹ繧ｯ繝医ャ繝予ses_work\ 驟堺ｸ九�ｮ縺ｿ
- 譁�蟄励さ繝ｼ繝�: UTF-8繧貞ｸｸ縺ｫ譏守､ｺ
- API繧ｭ繝ｼ縺ｯ繝上�ｼ繝峨さ繝ｼ繝峨＠縺ｪ縺��ｼ�freee_token.json / config_source.json 縺九ｉ隱ｭ縺ｿ霎ｼ繧�ｼ�
- 譌｢蟄倥�ｮ隱崎ｨｼ繝輔ぃ繧､繝ｫ讒区�舌ｒ邯ｭ謖√☆繧具ｼ�freee_token.json / config_source.json 繧堤ｶ咏ｶ壼茜逕ｨ�ｼ�
- 隱崎ｨｼ譁ｹ蠑丞､画峩遖∵ｭ｢
- 謖�遉ｺ縺輔ｌ縺ｦ縺�縺ｪ縺�蜈ｨ菴薙Μ繝輔ぃ繧ｯ繧ｿ遖∵ｭ｢
- import謨ｴ逅�遖∵ｭ｢�ｼ域�守､ｺ逧�縺ｫ謖�遉ｺ縺輔ｌ縺溷ｴ蜷医�ｮ縺ｿ�ｼ�
- 譌｢蟄倥Ο繧ｰ蜑企勁遖∵ｭ｢
- 髢｢謨ｰ蜷榊､画峩譎ゅ�ｯ逅�逕ｱ繧剃ｺ句燕蝣ｱ蜻�
- 譁ｰ隕丈ｾ晏ｭ倩ｿｽ蜉遖∵ｭ｢�ｼ域�守､ｺ逧�縺ｫ險ｱ蜿ｯ縺輔ｌ縺溷ｴ蜷医�ｮ縺ｿ�ｼ�
- requirements.txt 繧貞享謇九↓螟画峩遖∵ｭ｢
- 螟画峩繝輔ぃ繧､繝ｫ縺ｯ譛螟ｧ3莉ｶ縲�4莉ｶ莉･荳翫↓縺ｪ繧句ｴ蜷医�ｯ莠句燕蝣ｱ蜻翫＠縺ｦ縺九ｉ螳溯｡�
- 譁ｰ隕上さ繝ｼ繝我ｽ懈�先凾縺ｯ蜍穂ｽ懃｢ｺ隱阪さ繝槭Φ繝峨ｂ謠千､ｺ

## 螳御ｺ�蝣ｱ蜻翫ヵ繧ｩ繝ｼ繝槭ャ繝�
```
## 螳御ｺ�蝣ｱ蜻�
- 菴懈��/螟画峩繝輔ぃ繧､繝ｫ: [繝代せ]
- 螟画峩讎りｦ�: [1縲�3陦珪
- 繝�繧ｹ繝育ｵ先棡: [pass/fail + 蜃ｺ蜉帙し繝槭Μ]
- 豕ｨ諢冗せ: [縺ゅｌ縺ｰ]
```

```

## outreach_system/outreach.py

```py
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from send_mail import MATSUNO_EMAIL, OUTREACH_FROM_EMAIL, SENDER_NAME, send_mail


BASE_DIR = Path(__file__).resolve().parent
TARGETS_PATH = BASE_DIR / "targets.csv"
HISTORY_PATH = BASE_DIR / "history.json"
RESULT_PATH = BASE_DIR / "result_outreach.json"
RESEND_DAYS = 180


def load_targets(path: Path = TARGETS_PATH) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(file)
        ]


def load_history(path: Path = HISTORY_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_history(history: dict[str, str], path: Path = HISTORY_PATH) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)
        file.write("\n")


def was_sent_recently(email: str, history: dict[str, str], now: datetime) -> bool:
    last_sent_text = history.get(email)
    if not last_sent_text:
        return False

    try:
        last_sent = datetime.fromisoformat(last_sent_text)
    except ValueError:
        return False

    return now - last_sent < timedelta(days=RESEND_DAYS)


def build_template(target: dict[str, str]) -> tuple[str, str, str]:
    contact_name = target["contact_name"] or "縺疲球蠖楢�"
    target_type = target["type"]
    sender_name = SENDER_NAME or "譚ｾ驥�"
    sender_name_with_family = f"譚ｾ驥� {SENDER_NAME}".rstrip()

    if target_type == "蜈�隲九￠":
        subject = "繧ｨ繝ｳ繧ｸ繝九い繝ｪ繝ｳ繧ｰ繝ｪ繧ｽ繝ｼ繧ｹ縺ｮ縺疲署譯�"
        template = "A"
        body = f"""{contact_name}讒�

縺贋ｸ冶ｩｱ縺ｫ縺ｪ縺｣縺ｦ縺翫ｊ縺ｾ縺吶よｪ蠑丈ｼ夂､ｾTERRA 譚ｾ驥弱→逕ｳ縺励∪縺吶�

SES繧ｨ繝ｳ繧ｸ繝九い縺ｮ縺疲署譯医↓縺ｦ縺秘｣邨｡縺輔○縺ｦ縺�縺溘□縺阪∪縺励◆縲�
Java/Python/繧､繝ｳ繝輔Λ遲峨∝ｹ�蠎�縺�繧ｹ繧ｭ繝ｫ繧ｻ繝�繝医�ｮ繧ｨ繝ｳ繧ｸ繝九い繧�
蜊ｳ譌･縲懊＃謠先｡亥庄閭ｽ縺ｧ縺吶�

縺碑�亥袖縺後＃縺悶＞縺ｾ縺励◆繧峨√♀豌苓ｻｽ縺ｫ縺碑ｿ比ｿ｡縺上□縺輔＞縲�

譬ｪ蠑丈ｼ夂､ｾTERRA
{sender_name_with_family}
{OUTREACH_FROM_EMAIL}
"""
        return subject, body, template

    subject = "繧ｨ繝ｳ繧ｸ繝九い諠�蝣ｱ莠､謠帙�ｻBP謠先声縺ｮ縺皮嶌隲�"
    template = "B"
    body = f"""{contact_name}讒�

縺贋ｸ冶ｩｱ縺ｫ縺ｪ縺｣縺ｦ縺翫ｊ縺ｾ縺吶よｪ蠑丈ｼ夂､ｾTERRA 譚ｾ驥弱→逕ｳ縺励∪縺吶�

蠑顔､ｾ縺ｯSES莠区･ｭ繧貞ｱ暮幕縺励※縺翫ｊ縲。P讒倥→縺ｮ諠�蝣ｱ莠､謠帙�ｻ逶ｸ莠呈署譯医ｒ
遨肴･ｵ逧�縺ｫ騾ｲ繧√※縺翫ｊ縺ｾ縺吶�

譯井ｻｶ繝ｻ莠ｺ蜩｡諠�蝣ｱ縺ｮ莠､謠帷ｭ峨√＃闊亥袖縺後＃縺悶＞縺ｾ縺励◆繧�
縺懊�ｲ縺頑ｰ苓ｻｽ縺ｫ縺碑ｿ比ｿ｡縺上□縺輔＞縲�

譬ｪ蠑丈ｼ夂､ｾTERRA
{sender_name}
{OUTREACH_FROM_EMAIL}
"""
    return subject, body, template


def make_detail(
    target: dict[str, str],
    status: str,
    template: str | None = None,
) -> dict[str, str | None]:
    return {
        "company": target.get("company", ""),
        "email": target.get("email", ""),
        "status": status,
        "template": template,
    }


def run_outreach(dry_run: bool = True) -> dict[str, object]:
    now = datetime.now()
    targets = load_targets()
    history = load_history()
    details: list[dict[str, str | None]] = []
    sent = 0
    skipped = 0

    print(f"dry_run={dry_run}")
    print(f"from={OUTREACH_FROM_EMAIL}, cc={MATSUNO_EMAIL}")

    for target in targets:
        company = target["company"]
        email = target["email"]
        memo = target["memo"]

        if "譁ｭ繧�" in memo:
            skipped += 1
            details.append(make_detail(target, "skip_譁ｭ繧�"))
            print(f"[skip_譁ｭ繧馨 {company} <{email}>")
            continue

        if not email:
            skipped += 1
            details.append(make_detail(target, "skip_email縺ｪ縺�"))
            print(f"[skip_email縺ｪ縺余 {company}")
            continue

        if was_sent_recently(email, history, now):
            skipped += 1
            details.append(make_detail(target, "skip_180譌･譛ｪ貅"))
            print(f"[skip_180譌･譛ｪ貅] {company} <{email}>")
            continue

        subject, body, template = build_template(target)
        print(f"[target] {company} <{email}> template={template}")
        send_mail(email, subject, body, dry_run=dry_run, cc_email=MATSUNO_EMAIL)

        sent += 1
        details.append(make_detail(target, "sent", template))
        if not dry_run:
            history[email] = now.isoformat(timespec="seconds")

    if not dry_run:
        save_history(history)

    result = {
        "run_at": now.isoformat(timespec="seconds"),
        "dry_run": dry_run,
        "total": len(targets),
        "sent": sent,
        "skipped": skipped,
        "details": details,
    }

    with RESULT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"total={len(targets)}, sent={sent}, skipped={skipped}")
    print(f"result={RESULT_PATH}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Outreach mail sender")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="騾∽ｿ｡縺帙★繝ｭ繧ｰ縺ｮ縺ｿ蜃ｺ蜉帙＠縺ｾ縺�")
    mode.add_argument("--run", action="store_true", help="譛ｬ逡ｪ騾∽ｿ｡縺励∪縺�")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dry_run = not args.run
    run_outreach(dry_run=dry_run)


if __name__ == "__main__":
    main()

```

## outreach_system/send_mail.py

```py
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

from dotenv import dotenv_values


ENV_PATH = r"C:\Users\ma_py\OneDrive\繝�繧ｹ繧ｯ繝医ャ繝予ses_work\config\.env"
SMTP_HOST = "mail65.onamae.ne.jp"
SMTP_PORT = 465
MATSUNO_EMAIL = "r-matsuno@terra-ltd.co.jp"

config = dotenv_values(ENV_PATH)
OUTREACH_FROM_EMAIL = config.get("OUTREACH_FROM_EMAIL", MATSUNO_EMAIL)
OUTREACH_MAIL_PASSWORD = config.get(
    "OUTREACH_MAIL_PASSWORD",
    config.get("SESSALES_MAIL_PASSWORD", ""),
)
SENDER_NAME = config.get("SENDER_NAME", "")


def send_mail(
    to_email: str,
    subject: str,
    body: str,
    *,
    dry_run: bool = True,
    cc_email: str = MATSUNO_EMAIL,
) -> bool:
    if dry_run:
        print(f"[dry_run] send_mail skipped: to={to_email}, cc={cc_email}, subject={subject}")
        return True

    if not OUTREACH_MAIL_PASSWORD:
        raise RuntimeError("OUTREACH_MAIL_PASSWORD or SESSALES_MAIL_PASSWORD is not set.")

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = OUTREACH_FROM_EMAIL
    message["To"] = to_email
    message["Cc"] = cc_email
    message["Date"] = formatdate(localtime=True)

    recipients = [to_email]
    if cc_email:
        recipients.append(cc_email)

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(OUTREACH_FROM_EMAIL, OUTREACH_MAIL_PASSWORD)
        smtp.sendmail(OUTREACH_FROM_EMAIL, recipients, message.as_string())

    return True

```

## sales_pipeline/pipeline.py

```py
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from step1_generate import generate_intent_drafts
from step2_send import send_intent_drafts
from step3_parse import parse_unread_replies
from step4_judge import judge_all
from step5_proposal import generate_proposals
from step6_send_proposal import send_proposals


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase1 蝟ｶ讌ｭ繝代う繝励Λ繧､繝ｳ")
    parser.add_argument("--dry-run", action="store_true", help="繝｡繝ｼ繝ｫ騾∽ｿ｡縺ｨ螟夜Κ蜿門ｾ励ｒ繧ｹ繧ｭ繝�繝�")
    args = parser.parse_args()
    dry_run = bool(args.dry_run)
    try:
        generate_intent_drafts()
        send_intent_drafts(dry_run=dry_run)
        parse_unread_replies(dry_run=dry_run)
        judge_all()
        generate_proposals()
        send_proposals(dry_run=dry_run)
        return 0
    except Exception as exc:
        print(f"[pipeline] 繧ｨ繝ｩ繝ｼ: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

```

## sales_pipeline/step1_generate.py

```py
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
        print(f"[Step1] result.json隱ｭ霎ｼ繧ｨ繝ｩ繝ｼ: {exc}", flush=True)
        return []


def _skills(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, dict):
        return [str(k) for k in value.keys()]
    return []


def _candidate_name(candidate: dict) -> str:
    return candidate.get("name") or candidate.get("engineer_name") or candidate.get("engineer_id") or "蛟呵｣懆�"


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
                affiliation=candidate.get("affiliation") or "縺疲園螻樔ｼ夂､ｾ",
                contact_name=candidate.get("contact_name") or "縺疲球蠖楢�",
                project_name=project.get("project_name") or "譯井ｻｶ蜷肴悴險ｭ螳�",
                description=project.get("description") or project.get("project_url") or "",
                required_skills=", ".join(required) if required else "遒ｺ隱堺ｸｭ",
                preferred_skills=", ".join(preferred) if preferred else "遒ｺ隱堺ｸｭ",
                proposed_price=price,
                period=project.get("period") or project.get("start_date") or "遒ｺ隱堺ｸｭ",
                location=project.get("location") or "遒ｺ隱堺ｸｭ",
                remote=project.get("remote") or "遒ｺ隱堺ｸｭ",
                interview_count=project.get("interview_count") or "遒ｺ隱堺ｸｭ",
                foreign_ok="蜿ｯ" if project.get("foreign_ok") else "遒ｺ隱堺ｸｭ",
                required_format=skill_format(required),
                preferred_format=skill_format(preferred),
            )
            path = DRAFT_DIR / f"ikoukakunin_{project_id}_{_candidate_id(candidate)}.txt"
            path.write_text(f"Subject: {subject}\nTo: {candidate.get('contact_email', '')}\n\n{body}", encoding="utf-8")
            generated.append({"path": str(path), "project": project, "candidate": candidate, "subject": subject})
    print(f"[Step1] 諢丞髄遒ｺ隱阪Γ繝ｼ繝ｫ逕滓��: {len(generated)}莉ｶ", flush=True)
    return generated


if __name__ == "__main__":
    generate_intent_drafts()

```

## sales_pipeline/step2_send.py

```py
from __future__ import annotations

import json
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / "config" / ".env"
DRAFT_DIR = BASE_DIR / "drafts"
LOG_PATH = BASE_DIR / "logs" / "send_log.json"


def _env() -> dict:
    return dotenv_values(str(ENV_PATH))


def _split_draft(text: str) -> tuple[str, str, str]:
    subject = ""
    to = ""
    lines = text.splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
        elif line.lower().startswith("to:"):
            to = line.split(":", 1)[1].strip()
        elif line == "":
            body_start = i + 1
            break
    return to, subject, "\n".join(lines[body_start:])


def _append_log(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        logs = json.loads(LOG_PATH.read_text(encoding="utf-8")) if LOG_PATH.exists() else []
    except Exception:
        logs = []
    logs.append(entry)
    LOG_PATH.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")


def send_intent_drafts(dry_run: bool = True) -> list[dict]:
    cfg = _env()
    host = cfg.get("SESMAIL_HOST") or "localhost"
    port = cfg.get("SESMAIL_PORT") or "8766"
    endpoint = f"http://{host}:{port}/send"
    results = []
    for path in sorted(DRAFT_DIR.glob("ikoukakunin_*.txt")):
        to, subject, body = _split_draft(path.read_text(encoding="utf-8"))
        print(f"[Step2] 騾∽ｿ｡蟇ｾ雎｡: {to} / {subject}", flush=True)
        entry = {"step": "intent", "path": str(path), "to": to, "subject": subject, "dry_run": dry_run, "at": datetime.now().isoformat()}
        if dry_run:
            entry["status"] = "skipped"
            print("[Step2] dry-run: 繝｡繝ｼ繝ｫ騾∽ｿ｡繧ｹ繧ｭ繝�繝�", flush=True)
        else:
            payload = json.dumps({"account": "sessales", "to": to, "subject": subject, "body": body}, ensure_ascii=False).encode("utf-8")
            try:
                req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=30) as res:
                    entry["response"] = res.read().decode("utf-8", errors="replace")
                entry["status"] = "sent"
            except Exception as exc:
                entry["status"] = "error"
                entry["error"] = str(exc)
                print(f"[Step2] 騾∽ｿ｡繧ｨ繝ｩ繝ｼ: {exc}", flush=True)
        _append_log(entry)
        results.append(entry)
    if not results and dry_run:
        print("[Step2] dry-run: 繝｡繝ｼ繝ｫ騾∽ｿ｡繧ｹ繧ｭ繝�繝�", flush=True)
    return results


if __name__ == "__main__":
    send_intent_drafts(dry_run=True)

```

## sales_pipeline/step3_parse.py

```py
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / "config" / ".env"
PARSED_DIR = BASE_DIR / "parsed_replies"


def _fetch_recent(limit: int = 20, dry_run: bool = True) -> list[dict]:
    if dry_run:
        return []
    cfg = dotenv_values(str(ENV_PATH))
    host = cfg.get("SESMAIL_HOST") or "localhost"
    port = cfg.get("SESMAIL_PORT") or "8766"
    payload = json.dumps({"account": "sessales", "limit": limit}).encode("utf-8")
    for path in ("/unread", "/emails", "/recent"):
        try:
            req = urllib.request.Request(f"http://{host}:{port}{path}", data=payload, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=30) as res:
                data = json.loads(res.read().decode("utf-8"))
            return data.get("emails") or data.get("messages") or []
        except Exception as exc:
            print(f"[Step3] 繝｡繝ｼ繝ｫ蜿門ｾ励お繝ｩ繝ｼ({path}): {exc}", flush=True)
    return []


def _parse_skill_marks(body: str, title: str) -> dict:
    found = {}
    capture = False
    for line in body.splitlines():
        if title in line:
            capture = True
            continue
        if capture and line.startswith("笆ｼ"):
            break
        if capture:
            m = re.search(r"[繝ｻ\-]?\s*([^:�ｼ咯+)\s*[:�ｼ咯\s*([笳銀留ﾃ踊X])", line)
            if m:
                found[m.group(1).strip()] = "ﾃ�" if m.group(2).lower() in {"ﾃ�", "x"} else "笳�"
    return found


def parse_reply(email_item: dict) -> dict:
    body = email_item.get("body") or email_item.get("body_preview") or ""
    statuses = []
    for line in body.splitlines():
        if any(word in line for word in ("髱｢隲�隱ｿ謨ｴ荳ｭ", "髱｢隲�莠亥ｮ�", "邨先棡蠕�縺｡", "繧ｪ繝輔ぃ繝ｼ荳ｭ")):
            statuses.append(line.strip(" 繝ｻ\t"))
    return {
        "mail_id": str(email_item.get("id") or email_item.get("message_id") or "unknown"),
        "subject": email_item.get("subject", ""),
        "from": email_item.get("from", ""),
        "parallel_status": statuses,
        "required_skills": _parse_skill_marks(body, "蠢�鬆�"),
        "preferred_skills": _parse_skill_marks(body, "蟆壼庄"),
    }


def parse_unread_replies(dry_run: bool = True) -> list[dict]:
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    emails = _fetch_recent(dry_run=dry_run)
    parsed = []
    for item in emails:
        result = parse_reply(item)
        path = PARSED_DIR / f"{result['mail_id']}.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        parsed.append(result)
    print(f"[Step3] 譛ｪ隱ｭ繝｡繝ｼ繝ｫ遒ｺ隱�: {len(parsed)}莉ｶ", flush=True)
    return parsed


if __name__ == "__main__":
    parse_unread_replies(dry_run=True)

```

## sales_pipeline/step4_judge.py

```py
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PARSED_DIR = BASE_DIR / "parsed_replies"

STATUS_SCORES = {
    "髱｢隲�隱ｿ謨ｴ荳ｭ": 1.5,
    "髱｢隲�莠亥ｮ�": 2.0,
    "繧ｪ繝輔ぃ繝ｼ荳ｭ": 5.0,
}


def _result_wait_score(text: str) -> float:
    m = re.search(r"(\d+)\s*譌･", text)
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
        if "邨先棡蠕�縺｡" in status:
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
        reasons.append("荳ｦ陦後せ繧ｳ繧｢蜷郁ｨ�5.0莉･荳�")
    if any(v == "ﾃ�" for v in required.values()):
        reasons.append("蠢�鬆医せ繧ｭ繝ｫ縺ｫﾃ�")
    if gross_profit is not None and gross_profit < 5:
        reasons.append("邊怜茜5荳�蜀�譛ｪ貅")
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
            print(f"[Step4] 蛻､螳壹お繝ｩ繝ｼ({path.name}): {exc}", flush=True)
    ok = sum(1 for item in results if item.get("judge", {}).get("proposal_ok"))
    ng = len(results) - ok
    print(f"[Step4] 謠先｡亥庄蜷ｦ蛻､螳�: {ok}莉ｶOK / {ng}莉ｶNG", flush=True)
    return results


if __name__ == "__main__":
    judge_all()

```

## sales_pipeline/step5_proposal.py

```py
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
        print(f"[Step5] result.json隱ｭ霎ｼ繧ｨ繝ｩ繝ｼ: {exc}", flush=True)
    return []


def _skill_summary(value) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{k}:{v.get('result', v)}" if isinstance(v, dict) else f"{k}:{v}" for k, v in value.items()) or "遒ｺ隱堺ｸｭ"
    if isinstance(value, list):
        return ", ".join(map(str, value)) or "遒ｺ隱堺ｸｭ"
    return "遒ｺ隱堺ｸｭ"


def _summary(project: dict, candidates: list[dict]) -> str:
    cfg = dotenv_values(str(ENV_PATH))
    if cfg.get("ANTHROPIC_API_KEY"):
        names = "縲�".join(c.get("engineer_name") or c.get("name") or "蛟呵｣懆�" for c in candidates)
        return f"{project.get('project_name', '蟇ｾ雎｡譯井ｻｶ')}縺ｫ蟇ｾ縺励＋names}繧偵せ繧ｭ繝ｫ驕ｩ蜷亥ｺｦ縺ｨ蜊倅ｾ｡繝舌Λ繝ｳ繧ｹ縺ｧ驕ｸ螳壹＠縺ｾ縺励◆縲�"
    return "蛟呵｣懆�縺ｮ繧ｹ繧ｭ繝ｫ驕ｩ蜷亥ｺｦ縲∝腰萓｡縲∫ｨｼ蜒埼幕蟋区凾譛溘ｒ雕上∪縺医※謠先｡亥呵｣懊ｒ驕ｸ螳壹＠縺ｾ縺励◆縲�"


def generate_proposals() -> list[dict]:
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = []
    labels = ["譚ｾ", "遶ｹ", "譴�"]
    for project in _read_projects():
        candidates = sorted(project.get("candidates") or [], key=lambda c: c.get("score", 0), reverse=True)[:3]
        if not candidates:
            continue
        blocks = []
        for idx, candidate in enumerate(candidates):
            blocks.append(CANDIDATE_TEMPLATE.format(
                rank_label=labels[idx],
                name=candidate.get("engineer_name") or candidate.get("name") or "蛟呵｣懆�",
                price=candidate.get("proposed_price") or candidate.get("price") or "遒ｺ隱堺ｸｭ",
                available_date=candidate.get("available_date") or "遒ｺ隱堺ｸｭ",
                required=_skill_summary(candidate.get("required") or candidate.get("required_match")),
                preferred=_skill_summary(candidate.get("optional") or candidate.get("preferred_match")),
                appeal=f"繝槭ャ繝√Φ繧ｰ繧ｹ繧ｳ繧｢ {candidate.get('score', '遒ｺ隱堺ｸｭ')}",
            ))
        body = PROPOSAL_TEMPLATE.format(
            project_name=project.get("project_name") or "譯井ｻｶ蜷肴悴險ｭ螳�",
            candidate_blocks="\n".join(blocks),
            summary=_summary(project, candidates),
        )
        project_id = str(project.get("project_id") or project.get("id") or "project").replace("/", "_")
        path = DRAFT_DIR / f"proposal_{project_id}.txt"
        path.write_text(f"Subject: {project.get('project_name', '')} 縺疲署譯�\nTo: \n\n{body}", encoding="utf-8")
        outputs.append({"path": str(path), "project": project})
    print(f"[Step5] 謠先｡域枚逕滓��: {len(outputs)}莉ｶ", flush=True)
    return outputs


if __name__ == "__main__":
    generate_proposals()

```

## sales_pipeline/step6_send_proposal.py

```py
from __future__ import annotations

from step2_send import DRAFT_DIR, _append_log, _env, _split_draft

import json
import urllib.request
from datetime import datetime


def send_proposals(dry_run: bool = True) -> list[dict]:
    cfg = _env()
    host = cfg.get("SESMAIL_HOST") or "localhost"
    port = cfg.get("SESMAIL_PORT") or "8766"
    endpoint = f"http://{host}:{port}/send"
    results = []
    for path in sorted(DRAFT_DIR.glob("proposal_*.txt")):
        to, subject, body = _split_draft(path.read_text(encoding="utf-8"))
        print(f"[Step6] 騾∽ｿ｡蟇ｾ雎｡: {to} / {subject}", flush=True)
        entry = {"step": "proposal", "path": str(path), "to": to, "subject": subject, "dry_run": dry_run, "at": datetime.now().isoformat()}
        if dry_run:
            entry["status"] = "skipped"
            print("[Step6] dry-run: 謠先｡医Γ繝ｼ繝ｫ騾∽ｿ｡繧ｹ繧ｭ繝�繝�", flush=True)
        else:
            payload = json.dumps({"account": "sessales", "to": to, "subject": subject, "body": body}, ensure_ascii=False).encode("utf-8")
            try:
                req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=30) as res:
                    entry["response"] = res.read().decode("utf-8", errors="replace")
                entry["status"] = "sent"
            except Exception as exc:
                entry["status"] = "error"
                entry["error"] = str(exc)
                print(f"[Step6] 騾∽ｿ｡繧ｨ繝ｩ繝ｼ: {exc}", flush=True)
        _append_log(entry)
        results.append(entry)
    if not results and dry_run:
        print("[Step6] dry-run: 謠先｡医Γ繝ｼ繝ｫ騾∽ｿ｡繧ｹ繧ｭ繝�繝�", flush=True)
    return results


if __name__ == "__main__":
    send_proposals(dry_run=True)

```

## sales_pipeline/templates.py

```py
from __future__ import annotations


IKOUKAKUNIN_SUBJECT = "{candidate_name}讒� 譯井ｻｶ縺疲､懆ｨ弱�ｮ縺企｡倥＞�ｼ�{role_area}�ｼ�"

IKOUKAKUNIN_TEMPLATE = """{affiliation} {contact_name}讒�

縺�縺､繧ゅ♀荳冶ｩｱ縺ｫ縺ｪ縺｣縺ｦ縺翫ｊ縺ｾ縺吶�

莠ｺ蜩｡縺ｮ縺皮ｴｹ莉九≠繧翫′縺ｨ縺�縺斐＊縺�縺ｾ縺吶�
荳玖ｨ俶｡井ｻｶ縺�縺九′縺ｧ縺励ｇ縺�縺九�
縺疲､懆ｨ弱＞縺溘□縺代∪縺吶→蟷ｸ縺�縺ｧ縺吶�

縺ｾ縺溘√お繝ｳ繝医Μ繝ｼ縺�縺溘□縺代ｋ蝣ｴ蜷井ｸ玖ｨ�2轤ｹ縺疲蕗謗医＞縺溘□縺代∪縺吶→蟷ｸ縺�縺ｧ縺吶�
繝ｻ荳ｦ陦檎憾豕�
繝ｻ蠢�鬆医∝ｰ壼庄縺ｮ笳凝�

笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤
笆 譯井ｻｶ讎りｦ�
笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤
譯井ｻｶ蜷�    : {project_name}
讌ｭ蜍吝��螳ｹ  : {description}
蠢�鬆医せ繧ｭ繝ｫ: {required_skills}
蟆壼庄繧ｹ繧ｭ繝ｫ: {preferred_skills}
蜊倅ｾ｡      : {proposed_price}荳�蜀�
譛滄俣      : {period}
蜍､蜍吝慍    : {location}�ｼ医Μ繝｢繝ｼ繝亥庄蜷ｦ: {remote}�ｼ�
髱｢隲�      : {interview_count}蝗�
螟門嵜邀�    : {foreign_ok}

笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤
笆 縺碑ｨ伜�･繝輔か繝ｼ繝槭ャ繝�
笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤
笆ｼ蠢�鬆医せ繧ｭ繝ｫ�ｼ遺雷/ﾃ暦ｼ�
{required_format}
笆ｼ蟆壼庄繧ｹ繧ｭ繝ｫ�ｼ遺雷/ﾃ暦ｼ�
{preferred_format}

笆ｼ荳ｦ陦檎憾豕�
 萓具ｼ�
  繝ｻA遉ｾ: 髱｢隲�隱ｿ謨ｴ荳ｭ
  繝ｻB遉ｾ: 髱｢隲�莠亥ｮ� 2/2�ｼ遺雷譛遺雷譌･�ｼ�
  繝ｻC遉ｾ: 邨先棡蠕�縺｡ 2/2�ｼ磯擇隲�螳滓命譌･ 笳区怦笳区律�ｼ�

菴募穀繧医ｍ縺励￥縺企｡倥＞縺�縺溘＠縺ｾ縺吶�
"""

PROPOSAL_SUBJECT = "{project_name} 縺疲署譯�"

PROPOSAL_TEMPLATE = """縺疲球蠖楢�讒�

縺�縺､繧ゅ♀荳冶ｩｱ縺ｫ縺ｪ縺｣縺ｦ縺翫ｊ縺ｾ縺吶�
荳玖ｨ倥�ｮ騾壹ｊ縲∝呵｣懆�繧偵＃謠先｡医＞縺溘＠縺ｾ縺吶�

笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤
笆 譯井ｻｶ
笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤
{project_name}

笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤
笆 縺疲署譯亥呵｣懆�
笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤
{candidate_blocks}

笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤
笆 繧ｵ繝槭Μ繝ｼ
笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤
{summary}

縺皮｢ｺ隱阪�ｮ縺ｻ縺ｩ縲∽ｽ募穀繧医ｍ縺励￥縺企｡倥＞縺�縺溘＠縺ｾ縺吶�
"""

CANDIDATE_TEMPLATE = """縲須rank_label}縲捜name}
蜊倅ｾ｡: {price}荳�蜀�
遞ｼ蜒埼幕蟋�: {available_date}
蠢�鬆医せ繧ｭ繝ｫ: {required}
蟆壼庄繧ｹ繧ｭ繝ｫ: {preferred}
陬懆ｶｳ: {appeal}
"""


def skill_format(skills: list[str]) -> str:
    if not skills:
        return "繝ｻ迚ｹ縺ｫ縺ｪ縺�"
    return "\n".join(f"繝ｻ{skill}: " for skill in skills)

```

## mail_pipeline/mail_pipeline.py

```py
"""
mail_pipeline.py - v5.1
v4縺九ｉ縺ｮ螟画峩:
- 莠ｺ譚舌Γ繝ｼ繝ｫ蜿嶺ｿ｡譎�: 豺ｻ莉倥せ繧ｭ繝ｫ繧ｷ繝ｼ繝茨ｼ�PDF/Word/逕ｻ蜒擾ｼ峨ｒ閾ｪ蜍墓､懷�ｺ
- skill_reader縺ｧ繧ｹ繧ｭ繝ｫ謚ｽ蜃ｺ 竊� 譯井ｻｶ辣ｧ蜷� 竊� 邊怜茜繧ｸ繝｣繧ｹ繝域э蜷醍｢ｺ隱肴枚逕滓��
- 豺ｻ莉倥↑縺怜ｴ蜷医�ｯ繝｡繝ｼ繝ｫ譛ｬ譁�縺九ｉ繧ｹ繧ｭ繝ｫ謚ｽ蜃ｺ�ｼ亥ｾ捺擂騾壹ｊ�ｼ�
- 譯井ｻｶ逋ｻ骭ｲ譎ゅｂskill_reader縺ｮget_active_projects/match_skills繧貞茜逕ｨ
"""

import imaplib
import email
import re
import json
import os
import ssl
import base64
import requests
from datetime import date, datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from dotenv import dotenv_values
from pathlib import Path

# skill_reader繧偵う繝ｳ繝昴�ｼ繝�
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from skill_reader.skill_reader import (
    extract_skills_from_text, extract_skills_from_image,
    extract_text_from_pdf, extract_text_from_docx, pdf_to_base64_image,
    get_active_projects, match_skills, generate_iko_mail
)
from usage_tracker.cost_logger import log_cost

# ===== 險ｭ螳� =====
BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR.parent / "config" / ".env"
DRAFTS_DIR = BASE_DIR / "pipeline_drafts"
LOG_PATH = BASE_DIR / "pipeline.log"
PROCESSED_IDS_PATH = BASE_DIR / "processed_ids.json"

FETCH_LIMIT = 50
PROCESS_LIMIT = 20
MATCH_TOP_N = 10
DB_PROPERTY_CACHE = {}

config = dotenv_values(ENV_PATH)
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v

IMAP_SERVER   = os.environ.get("OUTLOOK_IMAP_SERVER", "mail65.onamae.ne.jp")
IMAP_PORT     = int(os.environ.get("OUTLOOK_IMAP_PORT", 993))
EMAIL_USER    = os.environ.get("OUTLOOK_EMAIL", "sessales@terra-ltd.co.jp")
EMAIL_PASS    = os.environ.get("OUTLOOK_PASSWORD", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
NOTION_KEY    = os.environ.get("NOTION_API_KEY", "")
ENGINEER_DB   = os.environ.get("NOTION_ENGINEER_DB_ID", "")
PROJECT_DB    = os.environ.get("NOTION_PROJECT_DB_ID", "")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

VALID_SKILLS = [
    "Java", "Python", "PHP", "JavaScript", "TypeScript", "C#", "Node.js",
    "React", "AWS", "繧､繝ｳ繝輔Λ", "Go", "Ruby", "Swift", "Kotlin", "Vue.js",
    "Angular", "Docker", "Kubernetes", "GCP", "Azure", "Spring",
    "MySQL", "PostgreSQL", "Oracle", "MongoDB", "Linux"
]

DOUBLE_CHECK_SYSTEM = f"""縺ゅ↑縺溘�ｯSES讌ｭ逡後�ｮ繝繝悶Ν繝√ぉ繝�繧ｯ蟆る摩AI縺ｧ縺吶�
謠先｡域枚縺ｨ蛟呵｣懆�諠�蝣ｱ繧貞女縺大叙繧翫∽ｻ･荳九�ｮ繝ｫ繝ｼ繝ｫ縺ｧ蜴ｳ蟇�縺ｫ繝√ぉ繝�繧ｯ縺励※縺上□縺輔＞縲�

莉頑律縺ｮ譌･莉�: {date.today().isoformat()}

縲�1. 髯､螟悶Ν繝ｼ繝ｫ驕募渚縲�
- 螟門嵜邀堺ｺｺ譚舌′蜷ｫ縺ｾ繧後※縺�縺ｪ縺�縺�
- 蝨ｰ譁ｹ蝨ｨ菴擾ｼ磯未譚ｱ莉･螟厄ｼ峨′蜷ｫ縺ｾ繧後※縺�縺ｪ縺�縺�
- 遏ｭ譛滓｡井ｻｶ騾｣邯壹�ｮ莠ｺ譚舌′蜷ｫ縺ｾ繧後※縺�縺ｪ縺�縺�
- 繝悶Λ繝ｳ繧ｯ縺後≠繧倶ｺｺ譚舌′蜷ｫ縺ｾ繧後※縺�縺ｪ縺�縺�
- 譌｢蠕豁ｴ縺後≠繧倶ｺｺ譚舌′蜷ｫ縺ｾ繧後※縺�縺ｪ縺�縺�

縲�2. 蜊倅ｾ｡繝√ぉ繝�繧ｯ�ｼ育ｲ怜茜�ｼ峨�
- 邊怜茜 = 譯井ｻｶ蜊倅ｾ｡ - 繧ｨ繝ｳ繧ｸ繝九い蜊倅ｾ｡
- 邊怜茜5荳�蜀�譛ｪ貅縺ｯNG / 邊怜茜7荳�蜀�莉･荳翫′逶ｮ讓�

縲�3. 荳ｦ陦後せ繧ｳ繧｢縲�
- 髱｢隲�隱ｿ謨ｴ荳ｭ:1.5 / 髱｢隲�莠亥ｮ�:2.0 / 邨先棡蠕�縺｡1-2譌･:2.5 / 3-7譌･:2.0 / 8-14譌･:1.5 / 15譌･雜�:1.0 / 繧ｪ繝輔ぃ繝ｼ荳ｭ:5.0
- 蜷郁ｨ�5.0莉･荳翫�ｯNG

縲�4. 謨ｬ隱槭�ｻ陦ｨ迴ｾ繝√ぉ繝�繧ｯ縲�
- 縲悟��雜ｳ縲坂�偵悟�ｨ縺ｦ貅縺溘＠縺ｦ縺翫ｊ縲�
- 縲悟叉謌ｦ蜉帙〒縺吶坂�偵後�槭ャ繝∝ｺｦ鬮倥＞莠ｺ蜩｡縺九→蟄倥§縺ｾ縺吶�

縲�5. 蝗ｺ譛牙錐隧槭�槭せ繧ｭ繝ｳ繧ｰ縲�
- 莨∵･ｭ蜷阪�ｻ諡�蠖楢�蜷阪�ｻ騾｣邨｡蜈医′谿九▲縺ｦ縺�縺ｪ縺�縺�

蜃ｺ蜉帙ヵ繧ｩ繝ｼ繝槭ャ繝�:
縲仙愛螳壹前K / NG
縲舌メ繧ｧ繝�繧ｯ邨先棡縲�
1. 髯､螟悶Ν繝ｼ繝ｫ: OK/NG�ｼ育炊逕ｱ�ｼ�
2. 蜊倅ｾ｡繝ｻ邊怜茜: OK/NG�ｼ郁ｩｳ邏ｰ�ｼ�
3. 荳ｦ陦後せ繧ｳ繧｢: OK/NG�ｼ郁ｩｳ邏ｰ�ｼ�
4. 謨ｬ隱櫁｡ｨ迴ｾ: OK/NG�ｼ井ｿｮ豁｣邂�謇�ｼ�
5. 繝槭せ繧ｭ繝ｳ繧ｰ: OK/NG�ｼ域ｼ上ｌ邂�謇�ｼ�
縲蝉ｿｮ豁｣貂医∩謠先｡域枚縲�
NG縺ｮ蝣ｴ蜷医�ｯ菫ｮ豁｣縺励◆謠先｡域枚縲＾K縺ｮ蝣ｴ蜷医�ｯ縲御ｿｮ豁｣荳崎ｦ√�
縲先園隕九�
豌励↓縺ｪ繧狗せ縺後≠繧後�ｰ荳險"""


# ===== 繝ｭ繧ｰ =====
def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def is_valid_iso_date(s) -> bool:
    if not s or not isinstance(s, str):
        return False
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', s.strip()))


def get_input_source_label(email_user: str) -> str:
    """IMAP繝ｭ繧ｰ繧､繝ｳ繧｢繧ｫ繧ｦ繝ｳ繝医°繧牙�･蜉帛��繝ｩ繝吶Ν繧定ｿ斐☆"""
    if "r-matsuno" in (email_user or ""):
        return "譚ｾ驥弱Γ繝ｼ繝ｫ"
    if "r-okamoto" in (email_user or ""):
        return "蟯｡譛ｬ繝｡繝ｼ繝ｫ"
    return "蜈ｱ騾壹Γ繝ｼ繝ｫ"


# ===== 蜃ｦ逅�貂医∩ID邂｡逅� =====
def load_processed_ids() -> set:
    try:
        if PROCESSED_IDS_PATH.exists():
            with open(PROCESSED_IDS_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except Exception as e:
        log(f"processed_ids隱ｭ縺ｿ霎ｼ縺ｿ繧ｨ繝ｩ繝ｼ: {e}")
    return set()


def save_processed_id(msg_id: str, processed: set):
    processed.add(msg_id)
    ids_list = list(processed)
    if len(ids_list) > 2000:
        ids_list = ids_list[1000:]
    try:
        with open(PROCESSED_IDS_PATH, "w", encoding="utf-8") as f:
            json.dump(ids_list, f, ensure_ascii=False)
    except Exception as e:
        log(f"processed_ids菫晏ｭ倥お繝ｩ繝ｼ: {e}")


# ===== 繝｡繝ｼ繝ｫ蜿門ｾ暦ｼ域ｷｻ莉倥ヵ繧｡繧､繝ｫ蟇ｾ蠢� v5譁ｰ隕擾ｼ�=====
def decode_str(s):
    if not s:
        return ""
    parts = decode_header(s)
    result = ""
    for part, charset in parts:
        if isinstance(part, bytes):
            result += part.decode(charset or "utf-8", errors="replace")
        else:
            result += str(part)
    return result


SKILL_SHEET_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "image/png", "image/jpeg", "image/jpg",
}

SKILL_SHEET_EXTENSIONS = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"}


def get_body_and_attachments(msg):
    """譛ｬ譁�繝�繧ｭ繧ｹ繝医→豺ｻ莉倥せ繧ｭ繝ｫ繧ｷ繝ｼ繝茨ｼ医ヰ繧､繝翫Μ+MIME繧ｿ繧､繝暦ｼ峨ｒ蜿門ｾ�"""
    body = ""
    attachments = []  # [{"data": bytes, "mime": str, "filename": str}]

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition  = str(part.get("Content-Disposition", ""))
        filename_raw = part.get_filename()
        filename     = decode_str(filename_raw) if filename_raw else ""

        # 譛ｬ譁�繝�繧ｭ繧ｹ繝�
        if content_type == "text/plain" and "attachment" not in disposition:
            charset = part.get_content_charset() or "utf-8"
            try:
                body = part.get_payload(decode=True).decode(charset, errors="replace")
            except Exception:
                pass
            continue

        # 豺ｻ莉倥ヵ繧｡繧､繝ｫ蛻､螳�
        ext = Path(filename).suffix.lower() if filename else ""
        is_skill_sheet = (
            content_type in SKILL_SHEET_MIME_TYPES or
            ext in SKILL_SHEET_EXTENSIONS
        )

        if is_skill_sheet and ("attachment" in disposition or filename):
            data = part.get_payload(decode=True)
            if data:
                # MIME繧ｿ繧､繝励ｒ豁｣隕丞喧
                mime = content_type
                if ext == ".pdf":
                    mime = "application/pdf"
                elif ext in (".docx", ".doc"):
                    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif ext in (".png",):
                    mime = "image/png"
                elif ext in (".jpg", ".jpeg"):
                    mime = "image/jpeg"
                attachments.append({"data": data, "mime": mime, "filename": filename})
                log(f"    豺ｻ莉俶､懷�ｺ: {filename} ({mime}) {len(data)}bytes")

    return body.strip(), attachments


def fetch_recent_emails(limit: int = 50):
    log(f"IMAP謗･邯夐幕蟋具ｼ育峩霑捜limit}莉ｶ蜿門ｾ暦ｼ�")
    ctx = ssl.create_default_context()
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=ctx)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")
    except Exception as e:
        log(f"IMAP謗･邯壹お繝ｩ繝ｼ: {e}")
        return []

    status, messages = mail.search(None, "ALL")
    if status != "OK" or not messages[0]:
        log("蟇ｾ雎｡繝｡繝ｼ繝ｫ縺ｪ縺�")
        mail.logout()
        return []

    all_ids = messages[0].split()
    target_ids = list(reversed(all_ids[-limit:]))
    log(f"蜈ｨ莉ｶ謨ｰ: {len(all_ids)}莉ｶ 竊� 逶ｴ霑捜len(target_ids)}莉ｶ繧貞�ｦ逅�蟇ｾ雎｡")

    emails = []
    for mail_id in target_ids:
        try:
            status, msg_data = mail.fetch(mail_id, "(RFC822)")
            if status != "OK":
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            subject  = decode_str(msg.get("Subject", ""))
            sender   = decode_str(msg.get("From", ""))
            reply_to = decode_str(msg.get("Reply-To", "")) or sender
            msg_id   = msg.get("Message-ID", f"no-id-{mail_id.decode()}")
            body, attachments = get_body_and_attachments(msg)
            emails.append({
                "id": mail_id, "msg_id": msg_id,
                "subject": subject, "sender": sender,
                "reply_to": reply_to, "body": body,
                "attachments": attachments  # v5霑ｽ蜉
            })
        except Exception as e:
            log(f"繝｡繝ｼ繝ｫ蜿門ｾ励お繝ｩ繝ｼ: {e}")

    mail.logout()
    log(f"蜿門ｾ怜ｮ御ｺ�: {len(emails)}莉ｶ")
    return emails


# ===== 繧ｹ繧ｭ繝ｫ繝輔ぅ繝ｫ繧ｿ繝ｪ繝ｳ繧ｰ =====
def filter_engineers_by_skills(project: dict, engineers: list, top_n: int = MATCH_TOP_N) -> list:
    required  = [s.lower() for s in project.get("required_skills", [])]
    optional  = [s.lower() for s in project.get("optional_skills", [])]
    proj_price = project.get("price", 0) or 0
    scored = []
    for eng in engineers:
        eng_skills = [s.lower() for s in eng.get("skills", [])]
        eng_price  = eng.get("price", 0) or 0
        if proj_price > 0 and eng_price > 0 and abs(proj_price - eng_price) > 5:
            continue
        req_match = sum(1 for r in required if any(r in s for s in eng_skills))
        if required and req_match == 0:
            continue
        opt_match = sum(1 for o in optional if any(o in s for s in eng_skills))
        scored.append((req_match * 2 + opt_match, eng))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [eng for _, eng in scored[:top_n]]


# ===== Claude AI =====
def call_claude(system: str, user: str, max_tokens: int = 1500) -> str:
    model = "claude-sonnet-4-6"
    try:
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}]
            },
            timeout=60
        )
        if res.status_code == 200:
            data = res.json()
            usage = data.get("usage", {})
            log_cost(
                script_name="mail_pipeline",
                model=data.get("model") or model,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cached_tokens=usage.get("cache_read_input_tokens", 0),
            )
            return data["content"][0]["text"]
        log(f"Claude API繧ｨ繝ｩ繝ｼ: {res.status_code} {res.text[:200]}")
        return ""
    except Exception as e:
        log(f"Claude蜻ｼ縺ｳ蜃ｺ縺嶺ｾ句､�: {e}")
        return ""


def classify_email(subject: str, body: str) -> dict:
    system = """縺ゅ↑縺溘�ｯSES讌ｭ逡後�ｮ諠�蝣ｱ隗｣譫植I縺ｧ縺吶ゅΓ繝ｼ繝ｫ繧定ｧ｣譫舌＠縺ｦJSON蠖｢蠑上�ｮ縺ｿ縺ｧ霑皮ｭ斐＠縺ｦ縺上□縺輔＞縲�

譯井ｻｶ諠�蝣ｱ縺ｮ蝣ｴ蜷�:
{"type":"project","name":"譯井ｻｶ蜷�","required_skills":["Java"],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"荳肴��","period":"","interview_count":1,"foreign_ok":false,"note":"讌ｭ蜍吝��螳ｹ"}

莠ｺ譚先ュ蝣ｱ縺ｮ蝣ｴ蜷�:
{"type":"engineer","name":"豌丞錐","skills":["Java"],"price":0,"available_date":"","experience_years":0,"company":"","note":"蛯呵�"}

縺ｩ縺｡繧峨〒繧ゅ↑縺�蝣ｴ蜷�:
{"type":"other","note":"蜀�螳ｹ隕∫ｴ�"}"""
    text = f"莉ｶ蜷�: {subject}\n\n{body[:2000]}"
    result = call_claude(system, text)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        parsed = json.loads(clean)
        return parsed if isinstance(parsed, dict) else {"type": "other", "note": "莠域悄縺励↑縺�蠖｢蠑�"}
    except:
        return {"type": "other", "note": "隗｣譫仙､ｱ謨�"}


def extract_affiliation(body: str) -> str:
    """繝｡繝ｼ繝ｫ譛ｬ譁�縺九ｉ謇螻樔ｼ夂､ｾ蜷阪ｒ謚ｽ蜃ｺ縲ょ叙繧後↑縺代ｌ縺ｰ遨ｺ譁�蟄励�"""
    if not ANTHROPIC_KEY or not body:
        return ""
    system = '繝｡繝ｼ繝ｫ譛ｬ譁�縺九ｉ騾∽ｿ｡蜈�縺ｾ縺溘�ｯ邏ｹ莉句��縺ｮ謇螻樔ｼ夂､ｾ蜷阪□縺代ｒ謚ｽ蜃ｺ縺励゛SON縺ｮ縺ｿ縺ｧ霑斐＠縺ｦ縺上□縺輔＞縲ょｽ｢蠑�: {"company":""}'
    result = call_claude(system, body[:2000], max_tokens=120)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        parsed = json.loads(clean)
        company = str(parsed.get("company", "")).strip() if isinstance(parsed, dict) else ""
        return company[:30]
    except Exception:
        return ""


def ai_matching(project: dict, engineers: list) -> dict:
    system = """縺ゅ↑縺溘�ｯSES讌ｭ逡後�ｮ繝槭ャ繝√Φ繧ｰAI縺ｧ縺吶�JSON縺ｧ霑斐＠縺ｦ縺上□縺輔＞縲�

髯､螟悶Ν繝ｼ繝ｫ:
- 蠢�鬆医せ繧ｭ繝ｫ縺ｫ笨� 竊� 髯､螟�
- 蜊倅ｾ｡荵夜屬5荳�雜� 竊� 髯､螟�

繧ｵ繝槭Μ繝ｼ譁��ｼ育ｦ∵ｭ｢: 蜈�雜ｳ繝ｻ蜊ｳ謌ｦ蜉帙〒縺呻ｼ�:
- 蠢�鬆亥�ｨ笳�+蟆壼庄蜈ｨ笳� 竊� "蠢�鬆医�ｻ蟆壼庄縺ｨ繧ゅ↓繝槭ャ繝∝ｺｦ鬮倥＞莠ｺ蜩｡"
- 蠢�鬆亥�ｨ笳�+蟆壼庄笳狗紫50%莉･荳� 竊� "蠢�鬆亥�ｨ縺ｦ貅縺溘＠縺ｦ縺翫ｊ縲∝ｰ壼庄繧や雷鬆�逶ｮ邨碁ｨ薙≠繧�"
- 蠢�鬆亥�ｨ笳九�ｮ縺ｿ 竊� "蠢�鬆医せ繧ｭ繝ｫ蜈ｨ縺ｦ貅縺溘＠蜊ｳ遞ｼ蜒榊庄閭ｽ"

霑皮ｭ斐ヵ繧ｩ繝ｼ繝槭ャ繝�:
{"candidates":[{"name":"豌丞錐","price":0,"summary":"繧ｵ繝槭Μ繝ｼ","required_match":{},"optional_match":{},"parallel":"縺ｪ縺�"}],"proposal_draft":"謠先｡医Γ繝ｼ繝ｫ譛ｬ譁�"}"""
    payload = {"project": project, "engineers": engineers}
    result = call_claude(system, json.dumps(payload, ensure_ascii=False), max_tokens=2000)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        return json.loads(clean)
    except:
        return {"candidates": [], "proposal_draft": ""}


def double_check(text: str) -> str:
    return call_claude(DOUBLE_CHECK_SYSTEM, text, max_tokens=2000)


# ===== Notion謫堺ｽ� =====
def get_database_property_names(db_id: str) -> set:
    if not db_id:
        return set()
    if db_id not in DB_PROPERTY_CACHE:
        try:
            res = requests.get(
                f"https://api.notion.com/v1/databases/{db_id}",
                headers=NOTION_HEADERS,
                timeout=30,
            )
            if res.status_code == 200:
                DB_PROPERTY_CACHE[db_id] = set(res.json().get("properties", {}).keys())
            else:
                log(f"Notion DB繝励Ο繝代ユ繧｣蜿門ｾ励せ繧ｭ繝�繝�: {res.status_code} {res.text[:120]}")
                DB_PROPERTY_CACHE[db_id] = set()
        except Exception as e:
            log(f"Notion DB繝励Ο繝代ユ繧｣蜿門ｾ嶺ｾ句､�: {e}")
            DB_PROPERTY_CACHE[db_id] = set()
    return DB_PROPERTY_CACHE[db_id]


def add_input_source_properties(properties: dict, db_id: str, input_source: str, affiliation: str):
    prop_names = get_database_property_names(db_id)
    if input_source and "蜈･蜉帛��" in prop_names:
        properties["蜈･蜉帛��"] = {"select": {"name": input_source}}
    if affiliation and "謇螻樔ｼ夂､ｾ蜷�" in prop_names:
        properties["謇螻樔ｼ夂､ｾ蜷�"] = {"rich_text": [{"text": {"content": affiliation[:500]}}]}


def notion_query(db_id: str, filter_obj: dict = None) -> list:
    results = []
    payload = {"page_size": 100}
    if filter_obj:
        payload["filter"] = filter_obj
    while True:
        r = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=NOTION_HEADERS, json=payload
        )
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results


def register_project(info: dict, subject: str, sender: str, input_source: str = "", affiliation: str = "") -> bool:
    name = info.get("name") or f"縲須subject[:20]}縲�"
    note = f"縲舌Γ繝ｼ繝ｫ縺九ｉ閾ｪ蜍慕匳骭ｲ縲曾n騾∽ｿ｡閠�: {sender}\n莉ｶ蜷�: {subject}\n\n{info.get('note','')}"
    properties = {
        "譯井ｻｶ蜷�": {"title": [{"text": {"content": name}}]},
        "繧ｹ繝�繝ｼ繧ｿ繧ｹ": {"select": {"name": "蜍滄寔荳ｭ"}},
        "譯井ｻｶ隧ｳ邏ｰ": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req:
        properties["蠢�隕√せ繧ｭ繝ｫ"] = {"multi_select": [{"name": s} for s in req]}
    if opt:
        properties["蟆壼庄繧ｹ繧ｭ繝ｫ"] = {"multi_select": [{"name": s} for s in opt]}
    if info.get("price"):
        properties["蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�"] = {"number": info["price"]}
    if is_valid_iso_date(info.get("start_date")):
        properties["髢句ｧ区律"] = {"date": {"start": info["start_date"].strip()}}
    if info.get("location"):
        properties["蜍､蜍吝慍"] = {"rich_text": [{"text": {"content": info["location"]}}]}
    add_input_source_properties(properties, PROJECT_DB, input_source, affiliation)
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": PROJECT_DB}, "properties": properties}
    )
    return res.status_code == 200


def register_engineer(info: dict, subject: str, sender: str, input_source: str = "", affiliation: str = "") -> tuple:
    """繧ｨ繝ｳ繧ｸ繝九い逋ｻ骭ｲ縲¨otion繝壹�ｼ繧ｸID繧りｿ斐☆"""
    name = info.get("name") or "�ｼ亥錐蜑肴悴險倩ｼ会ｼ�"
    note = f"縲舌Γ繝ｼ繝ｫ縺九ｉ閾ｪ蜍慕匳骭ｲ縲曾n騾∽ｿ｡閠�: {sender}\n莉ｶ蜷�: {subject}\n\n{info.get('note','')}"
    properties = {
        "蜷榊燕": {"title": [{"text": {"content": name}}]},
        "遞ｼ蜒咲憾豕�": {"select": {"name": "遞ｼ蜒榊庄閭ｽ"}},
        "蛯呵��ｼ�LINE繝｡繝｢�ｼ�": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    skills = [s for s in info.get("skills", []) if s in VALID_SKILLS]
    if skills:
        properties["繧ｹ繧ｭ繝ｫ"] = {"multi_select": [{"name": s} for s in skills]}
    if info.get("price"):
        properties["蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�"] = {"number": info["price"]}
    if is_valid_iso_date(info.get("available_date")):
        properties["遞ｼ蜒榊庄閭ｽ譌･"] = {"date": {"start": info["available_date"].strip()}}
    if info.get("experience_years"):
        properties["邨碁ｨ灘ｹｴ謨ｰ"] = {"number": info["experience_years"]}
    add_input_source_properties(properties, ENGINEER_DB, input_source, affiliation)
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": ENGINEER_DB}, "properties": properties}
    )
    if res.status_code == 200:
        return True, res.json().get("id", "")
    log(f"  [Notion ERROR engineer] {res.status_code}: {res.text[:300]}")
    return False, ""


def get_available_engineers() -> list:
    pages = notion_query(ENGINEER_DB, {
        "property": "遞ｼ蜒咲憾豕�", "select": {"equals": "遞ｼ蜒榊庄閭ｽ"}
    })
    engineers = []
    for p in pages:
        props = p["properties"]
        name_prop = props.get("蜷榊燕", {}).get("title", [])
        name   = name_prop[0]["plain_text"] if name_prop else "譛ｪ險倩ｼ�"
        skills = [o["name"] for o in props.get("繧ｹ繧ｭ繝ｫ", {}).get("multi_select", [])]
        price  = props.get("蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�", {}).get("number", 0) or 0
        avail  = (props.get("遞ｼ蜒榊庄閭ｽ譌･", {}).get("date") or {}).get("start", "")
        note_prop = props.get("蛯呵��ｼ�LINE繝｡繝｢�ｼ�", {}).get("rich_text", [])
        note   = note_prop[0]["plain_text"][:200] if note_prop else ""
        engineers.append({"name": name, "skills": skills, "price": price,
                          "available_date": avail, "note": note})
    return engineers


# ===== 繧ｹ繧ｭ繝ｫ繧ｷ繝ｼ繝亥�ｦ逅��ｼ�v5譁ｰ隕擾ｼ�=====
def process_skill_sheet(attachment: dict, engineer_price: int = None,
                        affiliation: str = "雋ｴ遉ｾ") -> dict | None:
    """
    豺ｻ莉倥せ繧ｭ繝ｫ繧ｷ繝ｼ繝医ｒ蜃ｦ逅�縺励※繧ｹ繧ｭ繝ｫ謚ｽ蜃ｺ繝ｻ譯井ｻｶ辣ｧ蜷医�ｻ諢丞髄遒ｺ隱肴枚繧堤函謌舌☆繧九�
    Returns: {"info": dict, "match_results": list, "iko_mail": str} or None
    """
    data = attachment["data"]
    mime = attachment["mime"]
    fname = attachment["filename"]

    log(f"    繧ｹ繧ｭ繝ｫ繧ｷ繝ｼ繝亥�ｦ逅�荳ｭ: {fname}")
    info = None

    try:
        if mime == "application/pdf":
            text = extract_text_from_pdf(data)
            if text:
                info = extract_skills_from_text(text)
            else:
                log("    (繝�繧ｭ繧ｹ繝医↑縺� 竊� 逕ｻ蜒丞､画鋤)")
                b64img = pdf_to_base64_image(data)
                if b64img:
                    info = extract_skills_from_image(b64img, "image/png")
        elif "word" in mime:
            text = extract_text_from_docx(data)
            info = extract_skills_from_text(text)
        elif mime.startswith("image/"):
            b64 = base64.standard_b64encode(data).decode()
            info = extract_skills_from_image(b64, mime)
    except Exception as e:
        log(f"    繧ｹ繧ｭ繝ｫ繧ｷ繝ｼ繝亥�ｦ逅�繧ｨ繝ｩ繝ｼ: {e}")
        return None

    if not info:
        log("    繧ｹ繧ｭ繝ｫ謚ｽ蜃ｺ螟ｱ謨�")
        return None

    log(f"    謚ｽ蜃ｺ繧ｹ繧ｭ繝ｫ: {', '.join(info.get('skills', []))}")

    # 譯井ｻｶ辣ｧ蜷�
    projects = get_active_projects()
    match_results = match_skills(info.get("skills", []), projects, engineer_price)

    # 諢丞髄遒ｺ隱阪Γ繝ｼ繝ｫ逕滓��
    iko_mail = generate_iko_mail(info, match_results, engineer_price, affiliation)

    just_count = sum(1 for r in match_results
                     if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12)
    log(f"    辣ｧ蜷亥ｮ御ｺ�: 謠先｡亥庄{sum(1 for r in match_results if r['proposable'])}莉ｶ "
        f"(邊怜茜繧ｸ繝｣繧ｹ繝�{just_count}莉ｶ)")

    return {"info": info, "match_results": match_results, "iko_mail": iko_mail}


# ===== 荳区嶌縺堺ｿ晏ｭ� =====
def save_draft(proj_name: str, reply_to: str, candidates: list,
               check_result: str, final_proposal: str,
               skill_result: dict = None):
    DRAFTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', proj_name)[:30]
    path = DRAFTS_DIR / f"{ts}_{safe_name}.txt"

    is_ok = "縲仙愛螳壹前K" in check_result

    content = f"""================================================================
謠先｡域枚荳区嶌縺� v5
逕滓�先律譎�: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================
縲先｡井ｻｶ蜷阪捜proj_name}
縲占ｿ比ｿ｡蜈医捜reply_to}

縲仙呵｣懆�縲�
"""
    for i, c in enumerate(candidates[:3], 1):
        content += f"  {'竭竭｡竭｢'[i-1]} {c['name']} / {c.get('price',0)}荳�蜀�\n"
        content += f"     {c.get('summary','')}\n"

    content += f"""
縲舌ム繝悶Ν繝√ぉ繝�繧ｯ邨先棡縲�
蛻､螳�: {'[OK]' if is_ok else '[NG]'}
{check_result[:800]}

縲先署譯医Γ繝ｼ繝ｫ譛ｬ譁��ｼ磯∽ｿ｡蜿ｯ閭ｽ迚茨ｼ峨�
{final_proposal}
================================================================
"""

    # v5: 繧ｹ繧ｭ繝ｫ繧ｷ繝ｼ繝育�ｧ蜷育ｵ先棡繧ゆｻ倩ｨ�
    if skill_result:
        just = [r for r in skill_result["match_results"]
                if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12]
        content += f"""
縲舌せ繧ｭ繝ｫ繧ｷ繝ｼ繝育�ｧ蜷育ｵ先棡�ｼ�skill_reader�ｼ峨�
豌丞錐: {skill_result['info'].get('name', '荳肴��')}
繧ｹ繧ｭ繝ｫ: {', '.join(skill_result['info'].get('skills', []))}
繝ｬ繝吶Ν: {skill_result['info'].get('level', '荳肴��')}

邊怜茜繧ｸ繝｣繧ｹ繝域｡井ｻｶTOP:
"""
        for r in just[:3]:
            content += f"  {r['project_name']} | 邊怜茜{r['gross']}荳Ⅸn"

        content += f"""
縲先э蜷醍｢ｺ隱阪Γ繝ｼ繝ｫ譁�髱｢縲�
{skill_result['iko_mail']}
================================================================
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def save_engineer_draft(engineer_info: dict, match_results: list,
                        iko_mail: str, reply_to: str, sender: str):
    """莠ｺ譚舌Γ繝ｼ繝ｫ蟆ら畑縺ｮ荳区嶌縺堺ｿ晏ｭ�"""
    DRAFTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = engineer_info.get("name", "荳肴��")
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', name)[:20]
    path = DRAFTS_DIR / f"{ts}_engineer_{safe_name}.txt"

    just = [r for r in match_results
            if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12]

    content = f"""================================================================
莠ｺ譚舌Γ繝ｼ繝ｫ蜃ｦ逅�邨先棡 v5
逕滓�先律譎�: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================
縲舌お繝ｳ繧ｸ繝九い縲捜name}
縲宣∽ｿ｡閠�縲捜sender}
縲占ｿ比ｿ｡蜈医捜reply_to}

縲先歓蜃ｺ繧ｹ繧ｭ繝ｫ縲捜', '.join(engineer_info.get('skills', []))}
縲舌Ξ繝吶Ν謗ｨ螳壹捜engineer_info.get('level', '荳肴��')}
縲先ｦりｦ√捜engineer_info.get('summary', '')}

縲千ｲ怜茜繧ｸ繝｣繧ｹ繝域｡井ｻｶ�ｼ�5縲�12荳��ｼ欝OP{len(just)}莉ｶ縲�
"""
    for r in just[:5]:
        req_str = "  ".join(f"{s}:{'笳�' if v else 'ﾃ�'}" for s, v in r["required"].items()) or "縺ｪ縺�"
        content += f"  {r['project_name']} ({r['client']}) | {r['project_price']}荳� | 邊怜茜{r['gross']}荳Ⅸn"
        content += f"    蠢�鬆�: {req_str}\n"

    content += f"""
縲先э蜷醍｢ｺ隱阪Γ繝ｼ繝ｫ譁�髱｢�ｼ育ｲ怜茜繧ｸ繝｣繧ｹ繝�TOP3�ｼ峨�
{iko_mail}
================================================================
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ===== 繝｡繧､繝ｳ =====
def main():
    log("=" * 50)
    log("繝｡繝ｼ繝ｫ繝代う繝励Λ繧､繝ｳ v5.1 襍ｷ蜍包ｼ亥�･蜉帛��繝ｩ繝吶Ν繝ｻ謇螻樔ｼ夂､ｾ蜷崎ｿｽ蜉�ｼ�")
    log(f"險ｭ螳�: 蜿門ｾ養FETCH_LIMIT}莉ｶ / 蜃ｦ逅�{PROCESS_LIMIT}莉ｶ / 繝槭ャ繝√Φ繧ｰ荳贋ｽ砿MATCH_TOP_N}蜷�")
    input_source = get_input_source_label(EMAIL_USER)
    log(f"蜈･蜉帛��: {input_source}")

    processed = load_processed_ids()
    log(f"蜃ｦ逅�貂医∩ID: {len(processed)}莉ｶ")

    emails = fetch_recent_emails(limit=FETCH_LIMIT)
    if not emails:
        log("蜃ｦ逅�蟇ｾ雎｡縺ｪ縺励�ｻ邨ゆｺ�")
        return

    new_emails = [e for e in emails if e["msg_id"] not in processed]
    log(f"譁ｰ隕丞�ｦ逅�蟇ｾ雎｡: {len(new_emails)}莉ｶ")

    if not new_emails:
        log("蜈ｨ縺ｦ蜃ｦ逅�貂医∩繝ｻ邨ゆｺ�")
        return

    target_emails = new_emails[:PROCESS_LIMIT]
    engineers = get_available_engineers()
    log(f"繧ｨ繝ｳ繧ｸ繝九いDB: {len(engineers)}蜷搾ｼ育ｨｼ蜒榊庄閭ｽ�ｼ�")

    for em in target_emails:
        subject     = em["subject"]
        sender      = em["sender"]
        reply_to    = em["reply_to"]
        body        = em["body"]
        msg_id      = em["msg_id"]
        attachments = em.get("attachments", [])

        log(f"蜃ｦ逅�荳ｭ: {subject[:50]}")
        if attachments:
            log(f"  豺ｻ莉�: {len(attachments)}莉ｶ")

        info = classify_email(subject, body)
        msg_type = info.get("type", "other")
        log(f"  蛻､螳�: {msg_type}")

        if msg_type == "project":
            affiliation = extract_affiliation(body)
            ok = register_project(info, subject, sender, input_source, affiliation)
            proj_name = info.get("name") or subject[:30]
            if not ok:
                log(f"  [NG] 譯井ｻｶNotion逋ｻ骭ｲ螟ｱ謨�")
                save_processed_id(msg_id, processed)
                continue
            log(f"  [OK] 譯井ｻｶ逋ｻ骭ｲ: {proj_name}")

            filtered = filter_engineers_by_skills(info, engineers, top_n=MATCH_TOP_N)
            log(f"  繧ｹ繧ｭ繝ｫ繝輔ぅ繝ｫ繧ｿ: {len(engineers)}蜷� 竊� {len(filtered)}蜷�")

            if not filtered:
                log(f"  [!!] 蛟呵｣懆�縺ｪ縺�")
                save_processed_id(msg_id, processed)
                continue

            matching = ai_matching(info, filtered)
            candidates = matching.get("candidates", [])
            proposal_draft = matching.get("proposal_draft", "")

            if not candidates:
                log(f"  [!!] AI繝槭ャ繝√Φ繧ｰ蛟呵｣懊↑縺�")
                save_processed_id(msg_id, processed)
                continue
            log(f"  AI繝槭ャ繝√Φ繧ｰ: {len(candidates)}蜷�")

            check_input = f"縲先｡井ｻｶ蜷阪捜proj_name}\n\n縲先署譯域枚繝峨Λ繝輔ヨ縲曾n{proposal_draft}\n\n縲仙呵｣懆�縲曾n"
            for c in candidates:
                check_input += f"- {c['name']} / {c.get('price',0)}荳�蜀� / 荳ｦ陦�: {c.get('parallel','縺ｪ縺�')}\n"
            check_result = double_check(check_input)

            final_proposal = proposal_draft
            marker = "縲蝉ｿｮ豁｣貂医∩謠先｡域枚縲�"
            if marker in check_result:
                after = check_result.split(marker, 1)[1].strip()
                if "縲先園隕九�" in after:
                    after = after.split("縲先園隕九�")[0].strip()
                if after and after != "菫ｮ豁｣荳崎ｦ�":
                    final_proposal = after

            # 譯井ｻｶ繝｡繝ｼ繝ｫ縺ｫ繧よｷｻ莉倥せ繧ｭ繝ｫ繧ｷ繝ｼ繝医′縺ゅｋ蝣ｴ蜷医�ｯ蜃ｦ逅�
            skill_result = None
            if attachments:
                skill_result = process_skill_sheet(
                    attachments[0],
                    engineer_price=None,
                    affiliation="雋ｴ遉ｾ"
                )

            draft_path = save_draft(proj_name, reply_to, candidates,
                                    check_result, final_proposal, skill_result)
            log(f"  [OK] 謠先｡域枚荳区嶌縺堺ｿ晏ｭ�: {draft_path.name}")

        elif msg_type == "engineer":
            # ===== v5: 繧ｹ繧ｭ繝ｫ繧ｷ繝ｼ繝域ｷｻ莉伜ｯｾ蠢� =====
            name = info.get("name", "�ｼ亥錐蜑肴悴險倩ｼ会ｼ�")
            eng_price = info.get("price") or None

            affiliation = extract_affiliation(body)
            skill_affiliation = affiliation or (sender.split("<")[0].strip() if "<" in sender else "雋ｴ遉ｾ")

            skill_result = None

            # 豺ｻ莉倥せ繧ｭ繝ｫ繧ｷ繝ｼ繝医′縺ゅｋ蝣ｴ蜷医�ｯskill_reader縺ｧ蜃ｦ逅�
            if attachments:
                log(f"  豺ｻ莉倥せ繧ｭ繝ｫ繧ｷ繝ｼ繝医ｒ蜃ｦ逅�: {attachments[0]['filename']}")
                skill_result = process_skill_sheet(
                    attachments[0],
                    engineer_price=eng_price,
                    affiliation=skill_affiliation
                )
                if skill_result:
                    # 繧ｹ繧ｭ繝ｫ謚ｽ蜃ｺ邨先棡縺ｧinfo.skills繧剃ｸ頑嶌縺搾ｼ医ｈ繧顔ｲｾ蠎ｦ縺碁ｫ倥＞�ｼ�
                    info["skills"] = skill_result["info"].get("skills", info.get("skills", []))
                    log(f"  繧ｹ繧ｭ繝ｫ繧ｷ繝ｼ繝医°繧峨せ繧ｭ繝ｫ荳頑嶌縺�: {info['skills']}")

            # Notion逋ｻ骭ｲ
            ok, notion_id = register_engineer(info, subject, sender, input_source, affiliation)
            if ok:
                log(f"  [OK] 莠ｺ譚千匳骭ｲ: {name} (Notion ID: {notion_id[:8]}...)")

                # skill_reader縺ｮ邨先棡縺後≠繧後�ｰNotion繧ｹ繧ｭ繝ｫ谺�繧よ峩譁ｰ貂医∩�ｼ�register_engineer縺ｧ逋ｻ骭ｲ�ｼ�
                # 莠ｺ譚蝉ｸ区嶌縺堺ｿ晏ｭ�
                if skill_result:
                    draft_path = save_engineer_draft(
                        skill_result["info"],
                        skill_result["match_results"],
                        skill_result["iko_mail"],
                        reply_to, sender
                    )
                    log(f"  [OK] 莠ｺ譚蝉ｸ区嶌縺堺ｿ晏ｭ�: {draft_path.name}")
                    just = sum(1 for r in skill_result["match_results"]
                               if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12)
                    log(f"  邊怜茜繧ｸ繝｣繧ｹ繝域｡井ｻｶ: {just}莉ｶ 竊� 諢丞髄遒ｺ隱肴枚逕滓�先ｸ医∩")
                else:
                    # 豺ｻ莉倥↑縺暦ｼ壽悽譁�縺九ｉ謚ｽ蜃ｺ縺励◆諠�蝣ｱ縺ｧ辣ｧ蜷医�ｮ縺ｿ
                    projects = get_active_projects()
                    match_results = match_skills(info.get("skills", []), projects, eng_price)
                    iko_mail = generate_iko_mail(info, match_results, eng_price, skill_affiliation)
                    draft_path = save_engineer_draft(info, match_results, iko_mail, reply_to, sender)
                    log(f"  [OK] 譛ｬ譁�繝吶�ｼ繧ｹ莠ｺ譚蝉ｸ区嶌縺堺ｿ晏ｭ�: {draft_path.name}")
            else:
                log(f"  [NG] 莠ｺ譚侵otion逋ｻ骭ｲ螟ｱ謨�: {name}")

        else:
            log(f"  繧ｹ繧ｭ繝�繝暦ｼ医◎縺ｮ莉厄ｼ�: {subject[:40]}")

        save_processed_id(msg_id, processed)

    log("繝｡繝ｼ繝ｫ繝代う繝励Λ繧､繝ｳ v5.1 螳御ｺ�")
    log("=" * 50)


if __name__ == "__main__":
    main()

```

## mail_pipeline/mail_pipeline_test1.py

```py
"""
繝｡繝ｼ繝ｫ繝代う繝励Λ繧､繝ｳ v4
- v3縺九ｉ縺ｮ螟画峩: 繝槭ャ繝√Φ繧ｰ蜑阪↓Python蛛ｴ縺ｧ繧ｹ繧ｭ繝ｫ繝輔ぅ繝ｫ繧ｿ繝ｪ繝ｳ繧ｰ�ｼ井ｸ贋ｽ�10蜷阪↓邨槭ｊ霎ｼ縺ｿ�ｼ�
- Notion繧ｨ繝ｳ繧ｸ繝九い4,642蜷阪ｒ縺昴�ｮ縺ｾ縺ｾAI縺ｫ貂｡縺吶→繝医�ｼ繧ｯ繝ｳ雜�驕� 竊� Python蛛ｴ縺ｧ繝輔ぅ繝ｫ繧ｿ繝ｪ繝ｳ繧ｰ蠕後↓貂｡縺�
"""

import imaplib
import email
import re
import json
import os
import ssl
import requests
from datetime import date, datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from dotenv import dotenv_values
from pathlib import Path

# ===== 險ｭ螳� =====
BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR.parent / "config" / ".env"
DRAFTS_DIR = BASE_DIR / "pipeline_drafts"
LOG_PATH = BASE_DIR / "pipeline.log"
PROCESSED_IDS_PATH = BASE_DIR / "processed_ids.json"

FETCH_LIMIT = 50
PROCESS_LIMIT = 1
MATCH_TOP_N = 10  # AI縺ｫ貂｡縺呎怙螟ｧ蛟呵｣懈焚

config = dotenv_values(ENV_PATH)
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v

IMAP_SERVER   = os.environ.get("OUTLOOK_IMAP_SERVER", "mail65.onamae.ne.jp")
IMAP_PORT     = int(os.environ.get("OUTLOOK_IMAP_PORT", 993))
EMAIL_USER    = os.environ.get("OUTLOOK_EMAIL", "sessales@terra-ltd.co.jp")
EMAIL_PASS    = os.environ.get("OUTLOOK_PASSWORD", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
NOTION_KEY    = os.environ.get("NOTION_API_KEY", "")
ENGINEER_DB   = os.environ.get("NOTION_ENGINEER_DB_ID", "")
PROJECT_DB    = os.environ.get("NOTION_PROJECT_DB_ID", "")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

VALID_SKILLS = [
    "Java", "Python", "PHP", "JavaScript", "TypeScript", "C#", "Node.js",
    "React", "AWS", "繧､繝ｳ繝輔Λ", "Go", "Ruby", "Swift", "Kotlin", "Vue.js",
    "Angular", "Docker", "Kubernetes", "GCP", "Azure", "Spring",
    "MySQL", "PostgreSQL", "Oracle", "MongoDB", "Linux"
]

DOUBLE_CHECK_SYSTEM = f"""縺ゅ↑縺溘�ｯSES讌ｭ逡後�ｮ繝繝悶Ν繝√ぉ繝�繧ｯ蟆る摩AI縺ｧ縺吶�
謠先｡域枚縺ｨ蛟呵｣懆�諠�蝣ｱ繧貞女縺大叙繧翫∽ｻ･荳九�ｮ繝ｫ繝ｼ繝ｫ縺ｧ蜴ｳ蟇�縺ｫ繝√ぉ繝�繧ｯ縺励※縺上□縺輔＞縲�

莉頑律縺ｮ譌･莉�: {date.today().isoformat()}

縲�1. 髯､螟悶Ν繝ｼ繝ｫ驕募渚縲�
- 螟門嵜邀堺ｺｺ譚舌′蜷ｫ縺ｾ繧後※縺�縺ｪ縺�縺�
- 蝨ｰ譁ｹ蝨ｨ菴擾ｼ磯未譚ｱ莉･螟厄ｼ峨′蜷ｫ縺ｾ繧後※縺�縺ｪ縺�縺�
- 遏ｭ譛滓｡井ｻｶ騾｣邯壹�ｮ莠ｺ譚舌′蜷ｫ縺ｾ繧後※縺�縺ｪ縺�縺�
- 繝悶Λ繝ｳ繧ｯ縺後≠繧倶ｺｺ譚舌′蜷ｫ縺ｾ繧後※縺�縺ｪ縺�縺�
- 譌｢蠕豁ｴ縺後≠繧倶ｺｺ譚舌′蜷ｫ縺ｾ繧後※縺�縺ｪ縺�縺�

縲�2. 蜊倅ｾ｡繝√ぉ繝�繧ｯ�ｼ育ｲ怜茜�ｼ峨�
- 邊怜茜 = 譯井ｻｶ蜊倅ｾ｡ - 繧ｨ繝ｳ繧ｸ繝九い蜊倅ｾ｡
- 邊怜茜5荳�蜀�譛ｪ貅縺ｯNG / 邊怜茜7荳�蜀�莉･荳翫′逶ｮ讓�

縲�3. 荳ｦ陦後せ繧ｳ繧｢縲�
- 髱｢隲�隱ｿ謨ｴ荳ｭ:1.5 / 髱｢隲�莠亥ｮ�:2.0 / 邨先棡蠕�縺｡1-2譌･:2.5 / 3-7譌･:2.0 / 8-14譌･:1.5 / 15譌･雜�:1.0 / 繧ｪ繝輔ぃ繝ｼ荳ｭ:5.0
- 蜷郁ｨ�5.0莉･荳翫�ｯNG

縲�4. 謨ｬ隱槭�ｻ陦ｨ迴ｾ繝√ぉ繝�繧ｯ縲�
- 縲悟��雜ｳ縲坂�偵悟�ｨ縺ｦ貅縺溘＠縺ｦ縺翫ｊ縲�
- 縲悟叉謌ｦ蜉帙〒縺吶坂�偵後�槭ャ繝∝ｺｦ鬮倥＞莠ｺ蜩｡縺九→蟄倥§縺ｾ縺吶�

縲�5. 蝗ｺ譛牙錐隧槭�槭せ繧ｭ繝ｳ繧ｰ縲�
- 莨∵･ｭ蜷阪�ｻ諡�蠖楢�蜷阪�ｻ騾｣邨｡蜈医′谿九▲縺ｦ縺�縺ｪ縺�縺�

蜃ｺ蜉帙ヵ繧ｩ繝ｼ繝槭ャ繝�:
縲仙愛螳壹前K / NG
縲舌メ繧ｧ繝�繧ｯ邨先棡縲�
1. 髯､螟悶Ν繝ｼ繝ｫ: OK/NG�ｼ育炊逕ｱ�ｼ�
2. 蜊倅ｾ｡繝ｻ邊怜茜: OK/NG�ｼ郁ｩｳ邏ｰ�ｼ�
3. 荳ｦ陦後せ繧ｳ繧｢: OK/NG�ｼ郁ｩｳ邏ｰ�ｼ�
4. 謨ｬ隱櫁｡ｨ迴ｾ: OK/NG�ｼ井ｿｮ豁｣邂�謇�ｼ�
5. 繝槭せ繧ｭ繝ｳ繧ｰ: OK/NG�ｼ域ｼ上ｌ邂�謇�ｼ�
縲蝉ｿｮ豁｣貂医∩謠先｡域枚縲�
NG縺ｮ蝣ｴ蜷医�ｯ菫ｮ豁｣縺励◆謠先｡域枚縲＾K縺ｮ蝣ｴ蜷医�ｯ縲御ｿｮ豁｣荳崎ｦ√�
縲先園隕九�
豌励↓縺ｪ繧狗せ縺後≠繧後�ｰ荳險"""


# ===== 繝ｭ繧ｰ =====
def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ===== 蜃ｦ逅�貂医∩ID邂｡逅� =====
def load_processed_ids() -> set:
    try:
        if PROCESSED_IDS_PATH.exists():
            with open(PROCESSED_IDS_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except Exception as e:
        log(f"processed_ids隱ｭ縺ｿ霎ｼ縺ｿ繧ｨ繝ｩ繝ｼ: {e}")
    return set()


def save_processed_id(msg_id: str, processed: set):
    processed.add(msg_id)
    ids_list = list(processed)
    if len(ids_list) > 2000:
        ids_list = ids_list[1000:]
    try:
        with open(PROCESSED_IDS_PATH, "w", encoding="utf-8") as f:
            json.dump(ids_list, f, ensure_ascii=False)
    except Exception as e:
        log(f"processed_ids菫晏ｭ倥お繝ｩ繝ｼ: {e}")


# ===== 繝｡繝ｼ繝ｫ蜿門ｾ� =====
def decode_str(s):
    if not s:
        return ""
    parts = decode_header(s)
    result = ""
    for part, charset in parts:
        if isinstance(part, bytes):
            result += part.decode(charset or "utf-8", errors="replace")
        else:
            result += str(part)
    return result


def get_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                try:
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    break
                except:
                    pass
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            body = msg.get_payload(decode=True).decode(charset, errors="replace")
        except:
            body = str(msg.get_payload())
    return body.strip()


def fetch_recent_emails(limit: int = 50):
    log(f"IMAP謗･邯夐幕蟋具ｼ育峩霑捜limit}莉ｶ蜿門ｾ暦ｼ�")
    ctx = ssl.create_default_context()
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=ctx)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")
    except Exception as e:
        log(f"IMAP謗･邯壹お繝ｩ繝ｼ: {e}")
        return []

    status, messages = mail.search(None, "ALL")
    if status != "OK" or not messages[0]:
        log("蟇ｾ雎｡繝｡繝ｼ繝ｫ縺ｪ縺�")
        mail.logout()
        return []

    all_ids = messages[0].split()
    target_ids = list(reversed(all_ids[-limit:]))
    log(f"蜈ｨ莉ｶ謨ｰ: {len(all_ids)}莉ｶ 竊� 逶ｴ霑捜len(target_ids)}莉ｶ繧貞�ｦ逅�蟇ｾ雎｡")

    emails = []
    for mail_id in target_ids:
        try:
            status, msg_data = mail.fetch(mail_id, "(RFC822)")
            if status != "OK":
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            subject  = decode_str(msg.get("Subject", ""))
            sender   = decode_str(msg.get("From", ""))
            reply_to = decode_str(msg.get("Reply-To", "")) or sender
            msg_id   = msg.get("Message-ID", f"no-id-{mail_id.decode()}")
            body     = get_body(msg)
            emails.append({
                "id": mail_id, "msg_id": msg_id,
                "subject": subject, "sender": sender,
                "reply_to": reply_to, "body": body
            })
        except Exception as e:
            log(f"繝｡繝ｼ繝ｫ蜿門ｾ励お繝ｩ繝ｼ: {e}")

    mail.logout()
    log(f"蜿門ｾ怜ｮ御ｺ�: {len(emails)}莉ｶ")
    return emails


# ===== 繧ｹ繧ｭ繝ｫ繝輔ぅ繝ｫ繧ｿ繝ｪ繝ｳ繧ｰ�ｼ遺��v4譁ｰ隕剰ｿｽ蜉笘��ｼ� =====
def filter_engineers_by_skills(project: dict, engineers: list, top_n: int = MATCH_TOP_N) -> list:
    """
    譯井ｻｶ縺ｮ蠢�鬆医�ｻ蟆壼庄繧ｹ繧ｭ繝ｫ縺ｧ繧ｨ繝ｳ繧ｸ繝九い繧偵ヵ繧｣繝ｫ繧ｿ繝ｪ繝ｳ繧ｰ縺嶺ｸ贋ｽ衡op_n蜷阪ｒ霑斐☆縲�
    繧ｹ繧ｳ繧｢ = 蠢�鬆医せ繧ｭ繝ｫ繝槭ャ繝∵焚*2 + 蟆壼庄繧ｹ繧ｭ繝ｫ繝槭ャ繝∵焚*1
    蠢�鬆医せ繧ｭ繝ｫ縺�1縺､繧ゅ�槭ャ繝√＠縺ｪ縺�蝣ｴ蜷医�ｯ髯､螟悶�
    蜊倅ｾ｡荵夜屬5荳�雜�繧る勁螟悶�
    """
    required = [s.lower() for s in project.get("required_skills", [])]
    optional = [s.lower() for s in project.get("optional_skills", [])]
    proj_price = project.get("price", 0) or 0

    scored = []
    for eng in engineers:
        eng_skills = [s.lower() for s in eng.get("skills", [])]
        eng_price = eng.get("price", 0) or 0

        # 蜊倅ｾ｡荵夜屬繝√ぉ繝�繧ｯ�ｼ�5荳�雜�縺ｯ髯､螟厄ｼ�
        if proj_price > 0 and eng_price > 0:
            if abs(proj_price - eng_price) > 5:
                continue

        # 蠢�鬆医せ繧ｭ繝ｫ繝槭ャ繝∵焚
        req_match = sum(1 for r in required if any(r in s for s in eng_skills))
        # 蠢�鬆医せ繧ｭ繝ｫ縺�1縺､繧ゅ↑縺代ｌ縺ｰ髯､螟厄ｼ亥ｿ�鬆医′謖�螳壹＆繧後※縺�繧句ｴ蜷医�ｮ縺ｿ�ｼ�
        if required and req_match == 0:
            continue

        # 蟆壼庄繧ｹ繧ｭ繝ｫ繝槭ャ繝∵焚
        opt_match = sum(1 for o in optional if any(o in s for s in eng_skills))

        score = req_match * 2 + opt_match
        scored.append((score, eng))

    # 繧ｹ繧ｳ繧｢髯埼�縺ｧ繧ｽ繝ｼ繝医∽ｸ贋ｽ衡op_n蜷阪ｒ霑斐☆
    scored.sort(key=lambda x: x[0], reverse=True)
    result = [eng for _, eng in scored[:top_n]]
    return result


# ===== Claude AI =====
def call_claude(system: str, user: str, max_tokens: int = 1500) -> str:
    try:
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}]
            },
            timeout=60
        )
        if res.status_code == 200:
            return res.json()["content"][0]["text"]
        log(f"Claude API繧ｨ繝ｩ繝ｼ: {res.status_code} {res.text[:200]}")
        return ""
    except Exception as e:
        log(f"Claude蜻ｼ縺ｳ蜃ｺ縺嶺ｾ句､�: {e}")
        return ""


def classify_email(subject: str, body: str) -> dict:
    system = """縺ゅ↑縺溘�ｯSES讌ｭ逡後�ｮ諠�蝣ｱ隗｣譫植I縺ｧ縺吶ゅΓ繝ｼ繝ｫ繧定ｧ｣譫舌＠縺ｦJSON蠖｢蠑上�ｮ縺ｿ縺ｧ霑皮ｭ斐＠縺ｦ縺上□縺輔＞縲�

譯井ｻｶ諠�蝣ｱ縺ｮ蝣ｴ蜷�:
{"type":"project","name":"譯井ｻｶ蜷�","required_skills":["Java"],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"荳肴��","period":"","interview_count":1,"foreign_ok":false,"note":"讌ｭ蜍吝��螳ｹ"}

莠ｺ譚先ュ蝣ｱ縺ｮ蝣ｴ蜷�:
{"type":"engineer","name":"豌丞錐","skills":["Java"],"price":0,"available_date":"","experience_years":0,"company":"","note":"蛯呵�"}

縺ｩ縺｡繧峨〒繧ゅ↑縺�蝣ｴ蜷�:
{"type":"other","note":"蜀�螳ｹ隕∫ｴ�"}"""
    text = f"莉ｶ蜷�: {subject}\n\n{body[:2000]}"
    result = call_claude(system, text)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        return json.loads(clean)
    except:
        return {"type": "other", "note": "隗｣譫仙､ｱ謨�"}


def ai_matching(project: dict, engineers: list) -> dict:
    system = """縺ゅ↑縺溘�ｯSES讌ｭ逡後�ｮ繝槭ャ繝√Φ繧ｰAI縺ｧ縺吶�JSON縺ｧ霑斐＠縺ｦ縺上□縺輔＞縲�

髯､螟悶Ν繝ｼ繝ｫ:
- 蠢�鬆医せ繧ｭ繝ｫ縺ｫ笨� 竊� 髯､螟�
- 蜊倅ｾ｡荵夜屬5荳�雜� 竊� 髯､螟厄ｼ域｡井ｻｶ蜊倅ｾ｡-5荳�縲�+2荳�縺ｮ遽�蝗ｲ縺ｮ縺ｿ�ｼ�

繧ｵ繝槭Μ繝ｼ譁��ｼ育ｦ∵ｭ｢: 蜈�雜ｳ繝ｻ蜊ｳ謌ｦ蜉帙〒縺呻ｼ�:
- 蠢�鬆亥�ｨ笳�+蟆壼庄蜈ｨ笳� 竊� "蠢�鬆医�ｻ蟆壼庄縺ｨ繧ゅ↓繝槭ャ繝∝ｺｦ鬮倥＞莠ｺ蜩｡"
- 蠢�鬆亥�ｨ笳�+蟆壼庄笳狗紫50%莉･荳� 竊� "蠢�鬆亥�ｨ縺ｦ貅縺溘＠縺ｦ縺翫ｊ縲∝ｰ壼庄繧や雷鬆�逶ｮ邨碁ｨ薙≠繧�"
- 蠢�鬆亥�ｨ笳九�ｮ縺ｿ 竊� "蠢�鬆医せ繧ｭ繝ｫ蜈ｨ縺ｦ貅縺溘＠蜊ｳ遞ｼ蜒榊庄閭ｽ"

霑皮ｭ斐ヵ繧ｩ繝ｼ繝槭ャ繝�:
{"candidates":[{"name":"豌丞錐","price":0,"summary":"繧ｵ繝槭Μ繝ｼ","required_match":{},"optional_match":{},"parallel":"縺ｪ縺�"}],"proposal_draft":"謠先｡医Γ繝ｼ繝ｫ譛ｬ譁�"}"""
    payload = {"project": project, "engineers": engineers}
    result = call_claude(system, json.dumps(payload, ensure_ascii=False), max_tokens=2000)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        return json.loads(clean)
    except:
        return {"candidates": [], "proposal_draft": ""}


def double_check(text: str) -> str:
    return call_claude(DOUBLE_CHECK_SYSTEM, text, max_tokens=2000)


# ===== Notion謫堺ｽ� =====
def notion_query(db_id: str, filter_obj: dict = None) -> list:
    results = []
    payload = {"page_size": 100}
    if filter_obj:
        payload["filter"] = filter_obj
    while True:
        r = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=NOTION_HEADERS, json=payload
        )
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results


def register_project(info: dict, subject: str, sender: str) -> bool:
    name = info.get("name") or f"縲須subject[:20]}縲�"
    note = f"縲舌Γ繝ｼ繝ｫ縺九ｉ閾ｪ蜍慕匳骭ｲ縲曾n騾∽ｿ｡閠�: {sender}\n莉ｶ蜷�: {subject}\n\n{info.get('note','')}"
    properties = {
        "譯井ｻｶ蜷�": {"title": [{"text": {"content": name}}]},
        "繧ｹ繝�繝ｼ繧ｿ繧ｹ": {"select": {"name": "蜍滄寔荳ｭ"}},
        "譯井ｻｶ隧ｳ邏ｰ": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req:
        properties["蠢�隕√せ繧ｭ繝ｫ"] = {"multi_select": [{"name": s} for s in req]}
    if opt:
        properties["蟆壼庄繧ｹ繧ｭ繝ｫ"] = {"multi_select": [{"name": s} for s in opt]}
    if info.get("price"):
        properties["蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�"] = {"number": info["price"]}
    if info.get("start_date"):
        properties["髢句ｧ区律"] = {"date": {"start": info["start_date"]}}
    if info.get("location"):
        properties["蜍､蜍吝慍"] = {"rich_text": [{"text": {"content": info["location"]}}]}
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": PROJECT_DB}, "properties": properties}
    )
    if res.status_code != 200:
        log(f"  [Notion ERROR project] {res.status_code}: {res.text[:300]}")
    return res.status_code == 200


def register_engineer(info: dict, subject: str, sender: str) -> bool:
    name = info.get("name") or "�ｼ亥錐蜑肴悴險倩ｼ会ｼ�"
    note = f"縲舌Γ繝ｼ繝ｫ縺九ｉ閾ｪ蜍慕匳骭ｲ縲曾n騾∽ｿ｡閠�: {sender}\n莉ｶ蜷�: {subject}\n\n{info.get('note','')}"
    properties = {
        "蜷榊燕": {"title": [{"text": {"content": name}}]},
        "遞ｼ蜒咲憾豕�": {"select": {"name": "遞ｼ蜒榊庄閭ｽ"}},
        "蛯呵��ｼ�LINE繝｡繝｢�ｼ�": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    skills = [s for s in info.get("skills", []) if s in VALID_SKILLS]
    if skills:
        properties["繧ｹ繧ｭ繝ｫ"] = {"multi_select": [{"name": s} for s in skills]}
    if info.get("price"):
        properties["蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�"] = {"number": info["price"]}
    if info.get("available_date"):
        properties["遞ｼ蜒榊庄閭ｽ譌･"] = {"date": {"start": info["available_date"]}}
    if info.get("experience_years"):
        properties["邨碁ｨ灘ｹｴ謨ｰ"] = {"number": info["experience_years"]}
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": ENGINEER_DB}, "properties": properties}
    )
    if res.status_code != 200:
        log(f"  [Notion ERROR engineer] {res.status_code}: {res.text[:300]}")
    return res.status_code == 200


def get_available_engineers() -> list:
    pages = notion_query(ENGINEER_DB, {
        "property": "遞ｼ蜒咲憾豕�", "select": {"equals": "遞ｼ蜒榊庄閭ｽ"}
    })
    engineers = []
    for p in pages:
        props = p["properties"]
        name_prop = props.get("蜷榊燕", {}).get("title", [])
        name   = name_prop[0]["plain_text"] if name_prop else "譛ｪ險倩ｼ�"
        skills = [o["name"] for o in props.get("繧ｹ繧ｭ繝ｫ", {}).get("multi_select", [])]
        price  = props.get("蜊倅ｾ｡�ｼ井ｸ�蜀��ｼ�", {}).get("number", 0) or 0
        avail  = (props.get("遞ｼ蜒榊庄閭ｽ譌･", {}).get("date") or {}).get("start", "")
        note_prop = props.get("蛯呵��ｼ�LINE繝｡繝｢�ｼ�", {}).get("rich_text", [])
        note   = note_prop[0]["plain_text"][:200] if note_prop else ""
        engineers.append({"name": name, "skills": skills, "price": price,
                          "available_date": avail, "note": note})
    return engineers


# ===== 謠先｡域枚荳区嶌縺堺ｿ晏ｭ� =====
def save_draft(proj_name: str, reply_to: str, candidates: list,
               check_result: str, final_proposal: str):
    DRAFTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', proj_name)[:30]
    path = DRAFTS_DIR / f"{ts}_{safe_name}.txt"

    is_ok = "縲仙愛螳壹前K" in check_result or "蛻､螳壹前K" in check_result

    content = f"""================================================================
謠先｡域枚荳区嶌縺�
逕滓�先律譎�: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================
縲先｡井ｻｶ蜷阪捜proj_name}
縲占ｿ比ｿ｡蜈医捜reply_to}

縲仙呵｣懆�縲�
"""
    for i, c in enumerate(candidates[:3], 1):
        content += f"  {'竭竭｡竭｢'[i-1]} {c['name']} / {c.get('price',0)}荳�蜀�\n"
        content += f"     {c.get('summary','')}\n"

    content += f"""
縲舌ム繝悶Ν繝√ぉ繝�繧ｯ邨先棡縲�
蛻､螳�: {'[OK] OK' if is_ok else '[NG] NG'}
{check_result[:800]}

縲先署譯医Γ繝ｼ繝ｫ譛ｬ譁��ｼ磯∽ｿ｡蜿ｯ閭ｽ迚茨ｼ峨�
{final_proposal}
================================================================
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ===== 繝｡繧､繝ｳ =====
def main():
    log("=" * 50)
    log(f"繝｡繝ｼ繝ｫ繝代う繝励Λ繧､繝ｳ v4 襍ｷ蜍包ｼ医せ繧ｭ繝ｫ繝輔ぅ繝ｫ繧ｿ繝ｪ繝ｳ繧ｰ霑ｽ蜉�ｼ�")
    log(f"險ｭ螳�: 蜿門ｾ養FETCH_LIMIT}莉ｶ / 蜃ｦ逅�{PROCESS_LIMIT}莉ｶ / 繝槭ャ繝√Φ繧ｰ荳贋ｽ砿MATCH_TOP_N}蜷�")

    processed = load_processed_ids()
    log(f"蜃ｦ逅�貂医∩ID: {len(processed)}莉ｶ")

    emails = fetch_recent_emails(limit=FETCH_LIMIT)
    if not emails:
        log("蜃ｦ逅�蟇ｾ雎｡縺ｪ縺励�ｻ邨ゆｺ�")
        return

    new_emails = [e for e in emails if e["msg_id"] not in processed]
    log(f"譁ｰ隕丞�ｦ逅�蟇ｾ雎｡: {len(new_emails)}莉ｶ�ｼ�{len(emails) - len(new_emails)}莉ｶ繧ｹ繧ｭ繝�繝暦ｼ�")

    if not new_emails:
        log("蜈ｨ縺ｦ蜃ｦ逅�貂医∩繝ｻ邨ゆｺ�")
        return

    target_emails = new_emails[:PROCESS_LIMIT]
    if len(new_emails) > PROCESS_LIMIT:
        log(f"蜃ｦ逅�荳企剞縺ｫ繧医ｊ{PROCESS_LIMIT}莉ｶ縺ｫ邨槭ｊ霎ｼ縺ｿ�ｼ域ｮ九ｊ{len(new_emails)-PROCESS_LIMIT}莉ｶ縺ｯ谺｡蝗橸ｼ�")

    engineers = get_available_engineers()
    log(f"繧ｨ繝ｳ繧ｸ繝九いDB: {len(engineers)}蜷搾ｼ育ｨｼ蜒榊庄閭ｽ�ｼ�")

    for em in target_emails:
        subject  = em["subject"]
        sender   = em["sender"]
        reply_to = em["reply_to"]
        body     = em["body"]
        msg_id   = em["msg_id"]
        log(f"蜃ｦ逅�荳ｭ: {subject[:50]}")

        info = classify_email(subject, body)
        msg_type = info.get("type", "other")
        log(f"  蛻､螳�: {msg_type}")

        if msg_type == "project":
            ok = register_project(info, subject, sender)
            proj_name = info.get("name") or subject[:30]
            if not ok:
                log(f"  [NG] 譯井ｻｶNotion逋ｻ骭ｲ螟ｱ謨�: {proj_name}")
                save_processed_id(msg_id, processed)
                continue
            log(f"  [OK] 譯井ｻｶ逋ｻ骭ｲ: {proj_name}")

            # 笘�v4: Python蛛ｴ縺ｧ繧ｹ繧ｭ繝ｫ繝輔ぅ繝ｫ繧ｿ繝ｪ繝ｳ繧ｰ笘�
            filtered = filter_engineers_by_skills(info, engineers, top_n=MATCH_TOP_N)
            log(f"  繧ｹ繧ｭ繝ｫ繝輔ぅ繝ｫ繧ｿ繝ｪ繝ｳ繧ｰ: {len(engineers)}蜷� 竊� {len(filtered)}蜷�")

            if not filtered:
                log(f"  [!!] 繧ｹ繧ｭ繝ｫ繝槭ャ繝√☆繧句呵｣懆�縺ｪ縺�: {proj_name}")
                save_processed_id(msg_id, processed)
                continue

            matching = ai_matching(info, filtered)
            candidates = matching.get("candidates", [])
            proposal_draft = matching.get("proposal_draft", "")

            if not candidates:
                log(f"  [!!] AI繝槭ャ繝√Φ繧ｰ蛟呵｣懊↑縺�: {proj_name}")
                save_processed_id(msg_id, processed)
                continue
            log(f"  AI繝槭ャ繝√Φ繧ｰ: {len(candidates)}蜷�")

            check_input = f"縲先｡井ｻｶ蜷阪捜proj_name}\n\n縲先署譯域枚繝峨Λ繝輔ヨ縲曾n{proposal_draft}\n\n縲仙呵｣懆�縲曾n"
            for c in candidates:
                check_input += f"- {c['name']} / {c.get('price',0)}荳�蜀� / 荳ｦ陦�: {c.get('parallel','縺ｪ縺�')}\n"
            check_result = double_check(check_input)

            final_proposal = proposal_draft
            marker = "縲蝉ｿｮ豁｣貂医∩謠先｡域枚縲�"
            if marker in check_result:
                after = check_result.split(marker, 1)[1].strip()
                if "縲先園隕九�" in after:
                    after = after.split("縲先園隕九�")[0].strip()
                if after and after != "菫ｮ豁｣荳崎ｦ�":
                    final_proposal = after

            draft_path = save_draft(proj_name, reply_to, candidates, check_result, final_proposal)
            log(f"  [OK] 謠先｡域枚荳区嶌縺堺ｿ晏ｭ�: {draft_path.name}")
            log(f"  [MAIL] 霑比ｿ｡蜈�: {reply_to}")

        elif msg_type == "engineer":
            name = info.get("name", "�ｼ亥錐蜑肴悴險倩ｼ会ｼ�")
            ok = register_engineer(info, subject, sender)
            if ok:
                log(f"  [OK] 莠ｺ譚千匳骭ｲ: {name}")
            else:
                log(f"  [NG] 莠ｺ譚侵otion逋ｻ骭ｲ螟ｱ謨�: {name}")

        else:
            log(f"  繧ｹ繧ｭ繝�繝暦ｼ医◎縺ｮ莉厄ｼ�: {subject[:40]}")

        save_processed_id(msg_id, processed)

    log("繝｡繝ｼ繝ｫ繝代う繝励Λ繧､繝ｳ v4 螳御ｺ�")
    log("=" * 50)


if __name__ == "__main__":
    main()

```

