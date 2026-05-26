# Jobz コード全体ダンプ

## matching_v2/matching_v2.py

```py
# -*- coding: utf-8 -*-
"""
AIスキル判定を使った案件 × エンジニア マッチング。

実行:
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
    return items[0]["plain_text"] if items else "（名前なし）"


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
    if "×" in required_results:
        return 0.0

    triangle_count = required_results.count("△")
    if triangle_count == 0:
        return 1.0
    if triangle_count == 1:
        return 0.8
    return 0.65


def needs_check(score, required_judgement):
    required_results = [item["result"] for item in required_judgement.values()]
    return score < 0.7 or "△" in required_results


def format_judgement(judgement):
    parts = []
    for skill, item in judgement.items():
        result = item["result"]
        reason = item.get("reason", "")
        if result == "△" and reason:
            parts.append(f"{skill}:{result}（{reason}）")
        else:
            parts.append(f"{skill}:{result}")
    return "  ".join(parts) if parts else "なし"


def extract_project(page):
    props = page["properties"]
    return {
        "id": page["id"],
        "url": page.get("url"),
        "name": get_title(props, "案件名"),
        "client": get_rich_text(props, "クライアント") or "不明",
        "required_skills": get_multiselect(props, "必要スキル"),
        "optional_skills": get_multiselect(props, "尚可スキル"),
        "price": get_number(props, "単価（万円）"),
        "start_date": get_date(props, "開始日"),
    }


def extract_engineer(page):
    props = page["properties"]
    return {
        "id": page["id"],
        "url": page.get("url"),
        "name": get_title(props, "名前"),
        "skills": get_multiselect(props, "スキル"),
        "price": get_number(props, "単価（万円）"),
        "available_date": get_date(props, "稼働可能日"),
    }


def make_project_result(project, candidates):
    return {
        "project_id": project["id"],
        "project_name": project["name"],
        "project_url": project["url"],
        # 2026-05-25: result.jsonで案件予算を確認できるようbudgetを追加。
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
    # 2026-05-25: 案件予算を大幅に超える単価の候補はスキル判定前に除外。
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
    print("AIマッチング結果")
    print("=" * 65)

    for project_result in projects_results:
        project = project_result["project"]
        candidates = project_result["candidates"]
        print(f"案件: {project['name']}")
        print(f"  クライアント: {project['client']}")
        print(f"  必須: {', '.join(project['required_skills']) or 'なし'}")
        print(f"  尚可: {', '.join(project['optional_skills']) or 'なし'}")

        if not candidates:
            print("  → 候補なし")
            print()
            continue

        for index, candidate in enumerate(candidates, start=1):
            engineer = candidate["engineer"]
            print(f"  候補{index}: {engineer['name']}（スコア: {candidate['score']:.2f}）")
            print(f"    必須: {format_judgement(candidate['required_judgement'])}")
            print(f"    尚可: {format_judgement(candidate['optional_judgement'])}")
            price = f"{engineer['price']}万" if engineer["price"] else "未設定"
            available_date = engineer["available_date"] or "未設定"
            print(f"    単価: {price} / 稼働: {available_date}")
            if candidate["needs_check"]:
                print("    → 要確認 ⚠️（松野に確認フラグ）")
            else:
                print("    → 提案推奨 ✅")
        print()


def validate_env():
    missing = [
        key for key in ["NOTION_API_KEY", "NOTION_ENGINEER_DB_ID", "ANTHROPIC_API_KEY"]
        if not os.environ.get(key)
    ]
    if missing:
        raise RuntimeError(f"必要な環境変数が未設定です: {', '.join(missing)}")


def validate_sample_env():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("必要な環境変数が未設定です: ANTHROPIC_API_KEY")


def load_sample_data():
    with open(SAMPLE_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    projects = []
    for project in data.get("projects", []):
        projects.append({
            "id": project["id"],
            "url": project.get("url"),
            "name": project["name"],
            "client": project.get("client", "サンプル"),
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
        help="test_data/sample.jsonを使い、Notion APIを呼ばずに実行する",
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
                "property": "ステータス",
                "select": {"equals": "募集中"},
            })
        ]
        engineers = [
            extract_engineer(page)
            for page in query_db(ENGINEER_DB_ID, {
                "property": "稼働状況",
                "select": {"equals": "稼働可能"},
            })
        ]

    print(f"募集中案件: {len(projects)}件 / 稼働可能エンジニア: {len(engineers)}名")

    cache = {}
    cache_lock = Lock()
    projects_results = []
    output_projects = []

    for project in projects:
        candidates = []
        if not project["required_skills"] and not project["optional_skills"]:
            print(f"判定スキップ: {project['name']}（スキル要件なし）", flush=True)
            projects_results.append({
                "project": project,
                "candidates": candidates,
            })
            output_projects.append(make_project_result(project, candidates))
            continue

        print(f"判定中: {project['name']}（{len(engineers)}名）", flush=True)

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

    # 2026-05-25: 尚可スキル空問題の原因調査用に件数を出力。
    optional_skill_projects = sum(1 for project in projects if project["optional_skills"])
    print(f"尚可スキルあり: {optional_skill_projects}/{len(projects)}件")

    print_summary(projects_results)
    print(f"result.json 生成: {RESULT_PATH}")


if __name__ == "__main__":
    main()

```

## matching_v2/notify_line.py

```py
# -*- coding: utf-8 -*-
"""
担当者別LINE通知スクリプト。

実行:
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
DEFAULT_ASSIGNEE = "松野"
OKAMOTO = "岡本"


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
    """NotionページのIDから担当者を取得。未設定・共通はデフォルト'松野'を返す。"""
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
    select_value = props.get("担当者", {}).get("select")
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
            "name": get_title_property(props, "案件名"),
            "detail": get_first_text_property(props, ["業務内容", "案件詳細", "詳細", "概要", "内容"]),
            "required_skills": get_first_multiselect_property(props, ["必須スキル", "必要スキル"]),
            "optional_skills": get_multiselect_property(props, "尚可スキル"),
            "price": get_number_property(props, "単価（万円）"),
            "start_date": get_date_property(props, "開始日"),
            "input_source": get_text_property(props, "入力元"),
            "affiliation": get_text_property(props, "所属会社名"),
        }

    if page_type == "engineer":
        return {
            "name": get_title_property(props, "名前"),
            "skills": get_multiselect_property(props, "スキル"),
            "price": get_number_property(props, "単価（万円）"),
            "available_date": get_date_property(props, "稼働可能日"),
            "input_source": get_text_property(props, "入力元"),
            "affiliation": get_text_property(props, "所属会社名"),
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
    line_prefix = "  ⚡LINE案件" if is_line_source(input_source) else ""
    lines = [
        "【マッチング結果】",
        f"案件: {format_value(project_info.get('name'))}{line_prefix}",
    ]
    if project_info.get("affiliation"):
        lines.append(f"所属: {project_info.get('affiliation')}")
    lines.extend([
        f"入力元: {format_value(input_source)}",
        f"業務内容: {format_value(project_info.get('detail'))}",
        f"必須: {format_list(project_info.get('required_skills'))}",
        f"尚可: {format_list(project_info.get('optional_skills'))}",
        f"単価: {format_price(project_info.get('price'))}",
        f"稼働: {format_value(project_info.get('start_date'))}",
        "──────────────",
    ])

    for item in candidate_infos:
        candidate = item["candidate"]
        engineer_info = item["engineer_info"]
        # 2026-05-25: needs_check候補が通知上で判別できるよう警告を追記。
        needs_check_warning = " ⚠️要確認" if candidate.get("needs_check") is True else ""
        lines.extend([
            f"▶ {format_value(engineer_info.get('name'))}（スコア: {format_score(candidate.get('score'))}）{needs_check_warning}",
        ])
        if engineer_info.get("affiliation"):
            lines.append(f"  所属: {engineer_info.get('affiliation')}")
        lines.extend([
            f"  入力元: {format_value(engineer_info.get('input_source'))}",
            (
                f"  単価: {format_price(engineer_info.get('price'))} / "
                f"稼働: {format_value(engineer_info.get('available_date'))}"
            ),
            f"  スキル: {format_list(engineer_info.get('skills'))}",
            f"  必須判定: {format_judgement(get_required_judgement(candidate))}",
            f"  尚可判定: {format_judgement(get_optional_judgement(candidate))}",
            "",
        ])

    lines.extend([
        "──────────────",
        "意向確認をお願いします。",
    ])
    return "\n".join(lines)


def is_line_source(input_source):
    return str(input_source or "").endswith("LINE")


def parse_args():
    parser = argparse.ArgumentParser(description="result.jsonを読み、担当者別にLINE Push通知します。")
    parser.add_argument("--dry-run", action="store_true", help="LINE送信せず通知内容をコンソール出力します。")
    parser.add_argument("--result-path", default=RESULT_PATH, help="読み込むresult.jsonのパス。")
    return parser.parse_args()


def get_project_id(item):
    project = item.get("project") or {}
    return project.get("id") or item.get("project_id") or ""


def get_project_name(item):
    project = item.get("project") or {}
    return project.get("name") or item.get("project_name") or "（案件名なし）"


def get_project_price(item):
    project = item.get("project") or {}
    return project.get("price") or item.get("price")


def get_project_start_date(item):
    project = item.get("project") or {}
    return project.get("start_date") or item.get("start_date")


def get_engineer_id(candidate):
    return candidate.get("id") or candidate.get("engineer_id") or ""


def get_engineer_name(candidate):
    return candidate.get("name") or candidate.get("engineer_name") or "（エンジニア名なし）"


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
        return "なし"

    parts = []
    for skill, value in judgement.items():
        result = value.get("result") if isinstance(value, dict) else value
        parts.append(f"{skill}:{result}")
    return " / ".join(parts)


def format_price(price):
    if price is None or price == "":
        return "未設定"
    return f"{price}万円"


def format_score(score):
    if score is None:
        return "未設定"
    if isinstance(score, float):
        return f"{score:.2f}".rstrip("0").rstrip(".")
    return str(score)


def format_list(values):
    items = [str(value) for value in (values or []) if value not in (None, "")]
    return ", ".join(items) if items else "なし"


def format_value(value):
    return str(value) if value not in (None, "") else "未設定"


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

- スキルシートPDF/画像をLINEから受信してskill_reader_api（8766）で処理

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

MATSUNO_USER_ID        = os.environ.get('MATSUNO_LINE_USER_ID') or 'REDACTED-SECRET'

OKAMOTO_CHANNEL_SECRET = os.environ.get('LINE_OKAMOTO_CHANNEL_SECRET') or os.environ.get('OKAMOTO_LINE_CHANNEL_SECRET', '')

OKAMOTO_CHANNEL_TOKEN  = os.environ.get('LINE_OKAMOTO_CHANNEL_TOKEN') or os.environ.get('OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN', '')

OKAMOTO_USER_ID        = os.environ.get('OKAMOTO_LINE_USER_ID') or 'REDACTED-SECRET'

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
        return "松野LINE"
    if user_id == OKAMOTO_USER_ID:
        return "岡本LINE"
    return "松野LINE"

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
    "東京都", "神奈川県", "埼玉県", "千葉県", "茨城県", "栃木県", "群馬県",
    "愛知県", "岐阜県", "三重県", "静岡県", "長野県", "富山県", "石川県",
    "福井県", "山梨県", "新潟県",
}

ALL_PREFECTURES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]

PREFECTURE_ALIASES = {
    pref.replace("都", "").replace("府", "").replace("県", ""): pref
    for pref in ALL_PREFECTURES
    if pref not in ("北海道", "京都府")
}
PREFECTURE_ALIASES["北海道"] = "北海道"

ENGINEER_NAME_NOT_FOUND_REPLY = "名前が取得できませんでした。「氏名: 〇〇」の形式で再送してください。"
AREA_OUT_OF_SCOPE_REPLY = "対応エリア外のため登録をスキップしました（関東・中部のみ対応）"



PENDING_PROPOSALS = {}

# スキルシート解析結果の一時保存 key: sender+"_skill" → iko_mail text

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

    msg = f"📊 案件『{proj_name}』登録・マッチング完了\n\n"



    if ok_candidates:

        msg += f"✅ OK候補: {len(ok_candidates)}名\n"

        for i, (c, detail) in enumerate(ok_candidates, 1):

            price = normalize_price(c.get("price", 0)) or 0

            msg += f"{i}. {c['name']} / {price}万\n"

            if detail: msg += f"   {detail}\n"

    else:

        msg += "✅ OK候補なし\n"



    if ng_candidates:

        msg += f"\n⚠️ 参考候補: {len(ng_candidates)}名\n"

        for i, (c, ng_reasons, detail) in enumerate(ng_candidates, 1):

            price = normalize_price(c.get("price", 0)) or 0

            msg += f"{i}. {c['name']} / {price}万\n"

            msg += f"   NG: {' / '.join(ng_reasons)}\n"

            if detail: msg += f"   {detail}\n"



    if proposal_draft:

        msg += f"\n提案文:\n{proposal_draft[:800]}"



    msg += "\n\n"

    if ok_candidates and ng_candidates:

        msg += "「送信して xxx@yyy.com」→ OK候補のみ\n「NGも含めて送信して xxx@yyy.com」→ 全員"

    elif ok_candidates:

        msg += "「送信して xxx@yyy.com」で意向確認メールを送ります"

    else:

        msg += "「NGも含めて送信して xxx@yyy.com」で参考候補を送れます"



    return msg





def build_reverse_match_message(eng_name, matches):

    if not matches:

        return f"📋 登録完了: {eng_name}\n\n⚠️ マッチする募集中案件なし"



    msg = f"📋 登録完了: {eng_name}\n\n🔎 マッチする案件 {len(matches)}件\n"

    for i, m in enumerate(matches[:3], 1):

        pname = m.get("project_name", "不明")

        pprice = m.get("project_price", 0)

        gross = m.get("gross_profit", 0)

        score = m.get("score", 0)

        req_match = m.get("required_match", {})

        req_str = " ".join(f"{'○' if v else '×'}{k}" for k, v in req_match.items()) if req_match else ""



        msg += f"\n{i}. {pname}\n"

        msg += f"   案件単価: {pprice}万 / 粗利予想: {gross}万 / スコア: {score}\n"

        if req_str: msg += f"   必須: {req_str}\n"



    if len(matches) > 3:

        msg += f"\n...他{len(matches)-3}件"



    return msg





def run_double_check(proposal_text, candidates_info):

    system = """SES proposal double-checker. Reply JSON only.

Check for:

1. Forbidden words: 弊社, 充足, 即戦力, 教えてください

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

    if input_source and "入力元" in get_database_property_names(db_id):

        props["入力元"] = {"select": {"name": input_source}}



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

        "名前": {"title": [{"text": {"content": name}}]},

        "稼働状況": {"select": {"name": "稼働可能"}},

        "備考（LINEメモ）": {"rich_text": [{"text": {"content": note[:2000]}}]}

    }

    assignee_name = "岡本" if user_id and user_id == OKAMOTO_USER_ID else "松野"
    props["担当者"] = {"select": {"name": assignee_name}}

    skills = [s for s in info.get("skills", []) if s in VALID_SKILLS]

    if skills: props["スキル"] = {"multi_select": [{"name": s} for s in skills]}

    price_val = normalize_price(info.get("price", 0))

    if price_val: props["単価（万円）"] = {"number": price_val}

    if info.get("experience_years"): props["経験年数"] = {"number": info["experience_years"]}

    if info.get("affiliation"):
        props["所属会社"] = {"rich_text": [{"text": {"content": info["affiliation"][:500]}}]}

    if info.get("contact_name"):
        props["所属担当者名"] = {"rich_text": [{"text": {"content": info["contact_name"][:100]}}]}

    if info.get("contact_email"):
        props["所属メール"] = {"email": info["contact_email"]}

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

        "案件名": {"title": [{"text": {"content": name}}]},

        "ステータス": {"select": {"name": "稼働中"}},

        "案件詳細": {"rich_text": [{"text": {"content": note[:2000]}}]}

    }

    assignee_name = "岡本" if user_id and user_id == OKAMOTO_USER_ID else "松野"
    props["担当者"] = {"select": {"name": assignee_name}}

    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]

    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]

    if req: props["必要スキル"] = {"multi_select": [{"name": s} for s in req]}

    if opt: props["尚可スキル"] = {"multi_select": [{"name": s} for s in opt]}

    price_val = normalize_price(info.get("price", 0))

    if price_val: props["単価（万円）"] = {"number": price_val}

    if info.get("location"): props["勤務地"] = {"rich_text": [{"text": {"content": info["location"]}}]}

    if info.get("period"): props["期間"] = {"rich_text": [{"text": {"content": info["period"]}}]}

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

        "property": "稼働状況", "select": {"equals": "稼働可能"}

    })

    result = []

    for p in pages:

        props = p["properties"]

        name_items = props.get("名前", {}).get("title", [])

        name = name_items[0].get("plain_text", "unknown") if name_items else "unknown"

        skills = [o["name"] for o in props.get("スキル", {}).get("multi_select", [])]

        price = props.get("単価（万円）", {}).get("number", 0) or 0

        note_items = props.get("備考（LINEメモ）", {}).get("rich_text", [])

        note = note_items[0].get("plain_text", "") if note_items else ""

        source = "unknown"

        if "line auto-register: matsuno" in note.lower(): source = "matsuno"

        elif "line auto-register: okamoto" in note.lower(): source = "okamoto"

        result.append({"name": name, "skills": skills, "price": price, "note": note[:300], "source": source})

    return result





def get_active_projects():
    # 募集中・稼働中・選考中すべてをマッチング対象とする
    pages = notion_query(NOTION_PROJECT_DB_ID, {
        "or": [
            {"property": "ステータス", "select": {"equals": "募集中"}},
            {"property": "ステータス", "select": {"equals": "稼働中"}},
            {"property": "ステータス", "select": {"equals": "選考中"}}
        ]
    })

    result = []

    for p in pages:

        props = p["properties"]

        name_items = props.get("案件名", {}).get("title", [])

        name = name_items[0].get("plain_text", "unknown") if name_items else "unknown"

        req_skills = [o["name"] for o in props.get("必要スキル", {}).get("multi_select", [])]

        opt_skills = [o["name"] for o in props.get("尚可スキル", {}).get("multi_select", [])]

        price = props.get("単価（万円）", {}).get("number", 0) or 0

        location_items = props.get("勤務地", {}).get("rich_text", [])

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

        print(f"[send_email] ERROR: パスワード未設定 account={account}")

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




# ── ステータス略語マッピング ──────────────────────────────────────
STATUS_ALIASES = {
    "前": "意向確認前",
    "確認": "意向確認中", "確認中": "意向確認中", "いこう": "意向確認中",
    "面談": "面談希望", "面談希望": "面談希望", "希望": "面談希望",
    "調整": "面談調整中", "調整中": "面談調整中",
    "済": "面談済み", "面談済": "面談済み", "済み": "面談済み",
    "合格": "合格", "ok": "合格", "OK": "合格", "〇": "合格",
    "ng": "NG", "NG": "NG", "×": "NG", "ばつ": "NG",
}

def normalize_status(raw):
    """略語をステータス正式名に変換"""
    return STATUS_ALIASES.get(raw.strip(), raw.strip())

def normalize_candidate_name(raw):
    """イニシャル・略称を正規化（ドット・スペース除去・大文字化）"""
    return raw.replace(".", "").replace(" ", "").replace("　", "").upper()

def find_candidate_in_text(text, name_query):
    """案件詳細テキストから候補者行を探す（部分一致）"""
    nq = normalize_candidate_name(name_query)
    for line in text.split("\n"):
        if "▶" not in line:
            continue
        # 行から候補者名部分を抽出（番号と単価の間）
        m = re.search(r"\d+\.\s+(.+?)\s+/", line)
        if m:
            cname = m.group(1).strip()
            if nq in normalize_candidate_name(cname):
                return line, cname
    return None, None

def update_candidate_status(page_id, candidate_name, new_status):
    """案件詳細の候補者ステータスを更新する"""
    r = requests.get(f"https://api.notion.com/v1/pages/{page_id}",
                     headers=NOTION_HEADERS, timeout=10)
    if r.status_code != 200:
        return False, f"案件取得失敗: {r.status_code}"

    props = r.json().get("properties", {})
    existing_items = props.get("案件詳細", {}).get("rich_text", [])
    existing_text = existing_items[0].get("plain_text", "") if existing_items else ""

    if not existing_text or "【候補者ステータス" not in existing_text:
        return False, "候補者ステータス欄が見つかりません"

    matched_line, matched_name = find_candidate_in_text(existing_text, candidate_name)
    if not matched_line:
        return False, f"「{candidate_name}」が見つかりません"

    new_line = re.sub(r"▶ .+$", f"▶ {new_status}", matched_line)
    updated_text = existing_text.replace(matched_line, new_line)[:1900]

    r2 = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=NOTION_HEADERS,
        json={"properties": {"案件詳細": {"rich_text": [{"type": "text", "text": {"content": updated_text}}]}}},
        timeout=10
    )
    if r2.status_code == 200:
        return True, matched_name
    return False, f"更新失敗: {r2.status_code}"


def find_projects_with_candidate(name_query):
    """候補者名で全案件を横断検索してヒットした(page_id, proj_name, matched_name)を返す"""
    pages = notion_query(NOTION_PROJECT_DB_ID, {
        "or": [
            {"property": "ステータス", "select": {"equals": "募集中"}},
            {"property": "ステータス", "select": {"equals": "稼働中"}},
            {"property": "ステータス", "select": {"equals": "選考中"}},
        ]
    })
    results = []
    for p in pages:
        props = p.get("properties", {})
        name_items = props.get("案件名", {}).get("title", [])
        proj_name = name_items[0].get("plain_text", "") if name_items else ""
        detail_items = props.get("案件詳細", {}).get("rich_text", [])
        detail_text = detail_items[0].get("plain_text", "") if detail_items else ""
        if "【候補者ステータス" not in detail_text:
            continue
        matched_line, matched_name = find_candidate_in_text(detail_text, name_query)
        if matched_line:
            results.append((p["id"], proj_name, matched_name))
    return results


def build_matching_result_reply():
    """Notion DBからリアルタイムでマッチング結果を取得してフォーマット"""
    try:
        # アクティブな案件を取得
        project_pages = notion_query(NOTION_PROJECT_DB_ID, {
            "or": [
                {"property": "ステータス", "select": {"equals": "募集中"}},
                {"property": "ステータス", "select": {"equals": "稼働中"}},
            ]
        })
        # 稼働可能なエンジニアを取得
        engineer_pages = notion_query(NOTION_ENGINEER_DB_ID, {
            "property": "稼働状況", "select": {"equals": "稼働可能"}
        })
    except Exception as e:
        print(f"[matching_reply] notion error: {e}")
        return "【マッチング結果】\nデータ取得失敗"

    if not project_pages or not engineer_pages:
        return f"【マッチング結果】{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n案件または人材データなし（案件:{len(project_pages)}件 人材:{len(engineer_pages)}名）"

    number_labels = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]
    lines = [f"【マッチング結果】{datetime.now().strftime('%Y-%m-%d %H:%M')}"]
    match_count = 0

    for pp in project_pages:
        props = pp.get("properties", {})
        # 案件名
        name_items = props.get("案件名", {}).get("title", [])
        proj_name = name_items[0].get("plain_text", "名称未設定") if name_items else "名称未設定"
        # 必須スキル
        req_skills = [o["name"] for o in props.get("必要スキル", {}).get("multi_select", [])]
        proj_price = props.get("単価（万円）", {}).get("number") or 0
        notion_url = f"https://www.notion.so/{pp['id'].replace('-', '')}"

        if not req_skills:
            continue  # スキル指定なし案件はスキップ

        # エンジニアとのスキルマッチング
        matched = []
        for ep in engineer_pages:
            eprops = ep.get("properties", {})
            ename_items = eprops.get("名前", {}).get("title", [])
            ename = ename_items[0].get("plain_text", "不明") if ename_items else "不明"
            eskills = [o["name"] for o in eprops.get("スキル", {}).get("multi_select", [])]
            eprice = eprops.get("単価（万円）", {}).get("number") or 0

            # 必須スキルが1つ以上一致すればマッチとする
            hit = [s for s in req_skills if s in eskills]
            if not hit:
                continue
            # 粗利チェック（5万以上）
            if eprice > 0 and proj_price > 0 and (proj_price - eprice) < 5:
                continue
            matched.append({"name": ename, "price": eprice, "hit": hit})

        if not matched:
            continue

        lines.append("")
        lines.append(f"■ {proj_name}（{len(matched)}名マッチ）")
        lines.append(notion_url)
        for idx, m in enumerate(matched[:2]):
            price_str = f"{m['price']}万" if m['price'] else "未設定"
            lines.append(f"  {number_labels[idx]} {m['name']} /{price_str}")
        if len(matched) > 2:
            lines.append(f"  他{len(matched)-2}名")
        match_count += 1

    if match_count == 0:
        return f"【マッチング結果】{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n現在マッチング候補なし\n（案件:{len(project_pages)}件 人材:{len(engineer_pages)}名で検索済み）"

    return "\n".join(lines)



def build_progress_reply():
    """案件進捗をReply API用にフォーマット"""
    try:
        pages = notion_query(NOTION_PROJECT_DB_ID, {
            "or": [
                {"property": "ステータス", "select": {"equals": "募集中"}},
                {"property": "ステータス", "select": {"equals": "選考中"}},
            ]
        })
    except Exception as e:
        print(f"[progress] notion error: {e}")
        return "【案件進捗】\nデータ取得失敗"

    weekdays = ["月","火","水","木","金","土","日"]
    now = datetime.now()
    header = f"【案件進捗】{now.strftime('%m/%d')}（{weekdays[now.weekday()]}）"
    lines = [header, ""]

    action_lines = []

    if not pages:
        lines.append("本日募集中案件なし")
        return "\n".join(lines)

    for p in pages:
        props = p.get("properties", {})
        name_items = props.get("案件名", {}).get("title", [])
        name = name_items[0].get("plain_text", "名称未設定") if name_items else "名称未設定"
        price = props.get("単価（万円）", {}).get("number")
        if price is None:
            price = props.get("単価(万円)", {}).get("number")
        if isinstance(price, float) and price.is_integer():
            price = int(price)
        price_str = str(price) if price not in (None, "") else "-"

        teian    = props.get("提案中",   {}).get("number") or 0
        mendan   = props.get("面談希望", {}).get("number") or 0
        ng       = props.get("NG",       {}).get("number") or 0
        goukaku  = props.get("合格",     {}).get("number") or 0
        seiyaku  = props.get("成約",     {}).get("number") or 0
        eigyo_end = props.get("営業終了", {}).get("number") or 0

        lines.append(f"■ {name}（{price_str}万）")
        row = f"  提案中:{teian} / 面談希望:{mendan} / NG:{ng} / 合格:{goukaku}"
        if seiyaku:
            row += f" / 成約:{seiyaku}"
        if eigyo_end:
            row += f" / 営業終了:{eigyo_end}"
        lines.append(row)
        lines.append("")

        if mendan > 0:
            action_lines.append(f"  {name} → 面談希望{mendan}件")

    lines.append("⚡ 要アクション")
    if action_lines:
        lines.extend(action_lines)
    else:
        lines.append("  なし")

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

    """LINEから送られたPDF/画像ファイルをskill_reader_apiで処理"""

    try:

        # LINEからファイルコンテンツ取得

        token = MATSUNO_CHANNEL_TOKEN if sender == "matsuno" else OKAMOTO_CHANNEL_TOKEN

        res = requests.get(

            f"https://api-data.line.me/v2/bot/message/{message_id}/content",

            headers={"Authorization": f"Bearer {token}"},

            timeout=30

        )

        if res.status_code != 200:

            reply_message(reply_token, f"❌ ファイル取得失敗: {res.status_code}", sender_token)

            return



        b64_data = base64.b64encode(res.content).decode()



        # skill_reader_api（8766）に送信

        reply_message(reply_token, "📋 スキルシート解析中...", sender_token)

        api_res = requests.post(

            "http://127.0.0.1:8766/process_skill_sheet",

            json={"base64": b64_data, "mime": mime_type, "affiliation": "貴社"},

            timeout=120

        )



        if api_res.status_code != 200:

            reply_message(reply_token, f"❌ 解析失敗: {api_res.text[:200]}", sender_token)

            return



        result = api_res.json()

        if result.get("status") != "ok":

            reply_message(reply_token, f"❌ 解析エラー: {result.get('message','不明')}", sender_token)

            return



        eng = result.get("engineer", {})

        name = eng.get("name", "不明")

        skills = ", ".join(eng.get("skills", [])) or "なし"

        level = eng.get("level", "不明")

        summary = eng.get("summary", "")

        just_count = result.get("just_count", 0)

        iko_mail = result.get("iko_mail", "")



        # 結果をPENDING_SKILL_MAILに保存

        pending_key = sender + "_skill"

        PENDING_SKILL_MAIL[pending_key] = iko_mail



        msg = f"📋 スキルシート解析完了\n"

        msg += f"氏名: {name}\n"

        msg += f"レベル: {level}\n"

        msg += f"スキル: {skills}\n"

        if summary:

            msg += f"概要: {summary}\n"

        msg += f"\n粗利ジャスト案件（5〜12万）: {just_count}件\n"

        msg += "\n「メール送信して xxx@yyy.com」で意向確認メールを送信できます。"



        push_message(

            MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID,

            msg,

            sender_token

        )



    except Exception as e:

        push_message(

            MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID,

            f"❌ スキルシート処理エラー: {str(e)[:200]}",

            sender_token

        )

        traceback.print_exc()





def handle_sheet_url(url, reply_token, sender, sender_token):

    reply_message(reply_token, "🔄 スプレッドシートを取得中...", sender_token)

    result = fetch_sheet_text(url)

    if result["status"] == "login_required":

        reply_message(reply_token, "⚠️ ログインが必要なスプレッドシートのためスキップしました", sender_token)

        return

    elif result["status"] == "error":

        reply_message(reply_token, f"❌ スプレッドシート取得失敗: {result.get('error','')[:100]}", sender_token)

        return



    text = result.get("text", "")

    if not text or len(text.strip()) < 50:

        reply_message(reply_token, "⚠️ スプレッドシートの内容が取得できませんでした", sender_token)

        return



    content_type = classify_sheet_content(text)

    raw_text = f"[スプレッドシート: {url}]\n{text}"



    if content_type == "project":

        projects = extract_projects_from_text(text)

        if not projects:

            reply_message(reply_token, "⚠️ 案件情報が抽出できませんでした", sender_token)

            return

        success_count = skip_count = 0

        for proj in projects:

            ok, _ = register_project(proj, raw_text, sender)

            if ok: success_count += 1

            else: skip_count += 1

        msg = f"📊 スプレッドシートから案件登録完了\n\n登録: {success_count}件 / スキップ: {skip_count}件\n"

        for i, p in enumerate(projects[:5], 1):

            msg += f"{i}. {p.get('name','(no name)')} / {p.get('price',0)}万\n"

        if len(projects) > 5: msg += f"...他{len(projects)-5}件"

        reply_message(reply_token, msg, sender_token)

    else:

        engineers = extract_engineers_from_text(text)

        if not engineers:

            reply_message(reply_token, "⚠️ 人員情報が抽出できませんでした", sender_token)

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

        msg = f"📊 スプレッドシートから人員登録完了\n\n登録: {success_count}名 / スキップ: {skip_count}名\n"

        if "name_not_found" in skip_reasons:

            msg += f"{ENGINEER_NAME_NOT_FOUND_REPLY}\n"

        if "area_out_of_scope" in skip_reasons:

            msg += f"{AREA_OUT_OF_SCOPE_REPLY}\n"

        for i, e in enumerate(engineers[:5], 1):

            msg += f"{i}. {e.get('name','(no name)')} / {e.get('price',0)}万\n"

        if len(engineers) > 5: msg += f"...他{len(engineers)-5}名"

        if registered:

            active_projects = deduplicate_projects(get_active_projects())

            if active_projects:

                msg += f"\n\n🔎 {len(registered)}名の逆マッチング中..."

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


    # ── リモートコマンド（松野のみ）─────────────────────────────────
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
        reply_message(reply_token, "❌ エラー\n権限がありません", sender_token)
        return



    # ── 送信指示の処理 ───────────────────────────────────────────

    is_send_all = "NGも含めて送信" in text_stripped or "NG含めて送信" in text_stripped

    is_mail_send = "メール送信して" in text_stripped

    is_send_ok  = text_stripped.startswith("送信して") or text_stripped.startswith("送信 ")



    # スキルシート解析後の意向確認メール送信

    if is_mail_send and skill_key in PENDING_SKILL_MAIL:

        emails = EMAIL_PATTERN.findall(text_stripped)

        to_addr = emails[0] if emails else None

        iko_mail = PENDING_SKILL_MAIL[skill_key]

        if to_addr:

            account = "matsuno" if sender == "matsuno" else "okamoto"

            subject = "案件ご検討のお願い"

            sent = send_email_via_callback(account, to_addr, subject, iko_mail)

            if sent:

                reply_message(reply_token, f"✅ 意向確認メール送信完了\n送信先: {to_addr}", sender_token)

                del PENDING_SKILL_MAIL[skill_key]

            else:

                reply_message(reply_token, f"❌ 送信失敗。以下をコピーして手動送信してください:\n宛先: {to_addr}\n\n{iko_mail[:2000]}", sender_token)

        else:

            reply_message(reply_token, f"📧 送信先メールアドレスを指定してください\n例: メール送信して xxx@yyy.com\n\n{iko_mail[:1500]}", sender_token)

        return



    # ── ステータス更新コマンド（簡略版）──────────────────────────────
    # 書式: 「更新 候補者名 ステータス略語」
    # 例:  「更新 RH 確認中」「更新 MY 面談」「更新 OA NG」
    if text_stripped.startswith("更新 ") or text_stripped.startswith("更新　"):
        parts = text_stripped[2:].strip().split()
        if len(parts) < 2:
            reply_message(reply_token,
                "書式: 更新 候補者名 ステータス\n"
                "例: 更新 RH 確認中 / 更新 MY 面談 / 更新 OA NG\n"
                "ステータス略語: 前 確認 面談 調整 済 合格 OK NG",
                sender_token)
            return
        name_query = parts[0]
        status_raw = parts[1]
        new_status = normalize_status(status_raw)
        valid = list(STATUS_ALIASES.values()) + list(STATUS_ALIASES.keys())
        if new_status not in ["意向確認前","意向確認中","面談希望","面談調整中","面談済み","合格","NG"]:
            reply_message(reply_token,
                f"「{status_raw}」は無効です\n略語: 前 確認 面談 調整 済 合格 OK NG",
                sender_token)
            return
        # 候補者名で案件を横断検索
        hits = find_projects_with_candidate(name_query)
        if not hits:
            reply_message(reply_token, f"「{name_query}」が候補者リストに見つかりません", sender_token)
            return
        if len(hits) > 1:
            # 複数案件にいる場合は一覧を返す → 「更新 RH 確認中 Java」で案件を絞れる案内
            names = "\n".join(f"{i+1}. {n}（{m}）" for i, (_, n, m) in enumerate(hits[:5]))
            if len(parts) >= 3:
                # 3つ目の引数を案件キーワードとして絞り込み
                proj_kw = parts[2]
                filtered = [(pid, pn, mn) for pid, pn, mn in hits if proj_kw.lower() in pn.lower()]
                if len(filtered) == 1:
                    hits = filtered
                else:
                    reply_message(reply_token,
                        f"複数案件にヒット:\n{names}\n\n絞り込み例: 更新 {name_query} {status_raw} Java",
                        sender_token)
                    return
            else:
                reply_message(reply_token,
                    f"「{name_query}」は複数案件に候補中:\n{names}\n\n案件を絞る場合: 更新 {name_query} {status_raw} 案件キーワード\n全件更新する場合: 更新 {name_query} {status_raw} 全部",
                    sender_token)
                return
        if len(parts) >= 3 and parts[2] == "全部":
            # 全案件一括更新
            success_list = []
            for pid, pn, mn in hits:
                ok, result = update_candidate_status(pid, mn, new_status)
                if ok:
                    success_list.append(pn[:20])
            reply_message(reply_token,
                f"✅ {len(success_list)}件更新\nステータス: {new_status}\n" + "\n".join(success_list),
                sender_token)
            return
        page_id, proj_name, matched_name = hits[0]
        ok, result = update_candidate_status(page_id, matched_name, new_status)
        if ok:
            reply_message(reply_token,
                f"✅ {matched_name} → {new_status}\n{proj_name[:30]}",
                sender_token)
        else:
            reply_message(reply_token, f"❌ 更新失敗: {result}", sender_token)
        return

    # マッチング結果照会

    if "マッチング" in text_stripped and len(text_stripped) <= 10:

        matching_reply = build_matching_result_reply()

        chunks = split_line_message(matching_reply)

        reply_message(reply_token, chunks[0], sender_token)

        push_user_id = user_id or (MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID)

        for chunk in chunks[1:]:

            push_message(push_user_id, chunk, sender_token)

        return


    # 案件進捗照会

    if "進捗" in text_stripped and len(text_stripped) <= 10:

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

            reply_message(reply_token, "⚠️ 送信待ちの提案がありません", sender_token)

            return



        emails = EMAIL_PATTERN.findall(text_stripped)

        to_addr = emails[0] if emails else None



        ok_list  = pending.get("ok", [])

        ng_list  = pending.get("ng", [])

        draft    = pending.get("proposal_draft", "")

        proj_name = pending.get("proj_name", "案件")



        target = ok_list + (ng_list if is_send_all else [])

        target_names = [c["name"] for c, *_ in target]



        if to_addr:

            account = "matsuno" if sender == "matsuno" else "okamoto"

            subject = f"【ご提案】{proj_name}"

            body = draft if draft else f"【ご提案】{proj_name}\n\n" + "\n".join(f"・{n}" for n in target_names)

            sent = send_email_via_callback(account, to_addr, subject, body)

            if sent:

                reply_message(reply_token,

                    f"✅ メール送信完了\n送信先: {to_addr}\n件名: {subject}\n対象: {len(target_names)}名",

                    sender_token)

            else:

                reply_message(reply_token,

                    f"❌ 自動送信失敗。以下をコピーして手動送信してください:\n送信先: {to_addr}\n\n{body[:1500]}",

                    sender_token)

        else:

            label = "全員" if is_send_all else "OK候補のみ"

            reply_message(reply_token,

                f"📋 提案内容確認（{label} {len(target_names)}名）\n送信先メールを「送信して xxx@yyy.com」で指定してください\n\n{draft[:1500]}",

                sender_token)

            return



        del PENDING_PROPOSALS[pending_key]

        return



    # ── スプレッドシートURL ──────────────────────────────────────

    sheet_urls = SHEET_URL_PATTERN.findall(text)

    if sheet_urls:

        handle_sheet_url(sheet_urls[0], reply_token, sender, sender_token)

        return



    # ── 通常メッセージ分類 ───────────────────────────────────────

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

            reply_message(reply_token, "❌ 登録失敗", sender_token)

            return

        active_projects = deduplicate_projects(get_active_projects())

        if not active_projects:

            name = info.get("name", "(no name)")

            skills_str = ", ".join(info.get("skills", [])) or "N/A"

            price = normalize_price(info.get("price", 0))

            reply_message(reply_token,

                f"📋 登録完了\n名前: {name}\nスキル: {skills_str}\n単価: {price}万\n\n稼働中案件なし",

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

            reply_message(reply_token, "❌ 人員情報が取得できませんでした", sender_token)

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

        msg = f"📊 複数人員登録完了\n登録: {success_count}名 / スキップ: {skip_count}名\n"

        if "name_not_found" in skip_reasons:

            msg += f"{ENGINEER_NAME_NOT_FOUND_REPLY}\n"

        if "area_out_of_scope" in skip_reasons:

            msg += f"{AREA_OUT_OF_SCOPE_REPLY}\n"

        for i, e in enumerate(engineers_list[:5], 1):

            msg += f"{i}. {e.get('name','(no name)')} / {e.get('price',0)}万\n"

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

            reply_message(reply_token, "❌ 案件登録失敗", sender_token)

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

            reply_message(reply_token, "❌ 案件情報が取得できませんでした", sender_token)

            return

        success_count = skip_count = 0

        for proj in projects_list:

            ok, _ = register_project(proj, text, sender, user_id=user_id)

            if ok: success_count += 1

            else: skip_count += 1

        msg = f"📊 複数案件登録完了\n登録: {success_count}件 / スキップ: {skip_count}件\n"

        for i, p in enumerate(projects_list[:5], 1):

            msg += f"{i}. {p.get('name','(no name)')} / {p.get('price',0)}万\n"

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

                # PDF/画像スキルシート受信

                mime = msg.get('contentType', 'image/jpeg') if msg_type == 'image' else msg.get('fileName', '')

                # ファイル名からMIME判定

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
ジョブズ用 ローカルコマンド実行サーバー
- localhost:8765 でHTTPリクエストを受け付ける
- ジョブズ（Claude）がFilesystem MCPまたはHTTP経由でコマンドを送信 → PC上で実行 → 結果を返す
- セキュリティ: localhostのみ受付、トークン認証あり
- v2: ThreadingHTTPServer化（長時間コマンドでブロックしない）
- v2: timeout上限3600秒（1時間）、/write_and_runもtimeoutをリクエストから受け取る
"""

import http.server
import json
import subprocess
import os
import sys
import logging
from datetime import datetime
from socketserver import ThreadingMixIn

# ========== 設定 ==========
PORT = 8765
AUTH_TOKEN = "jobz-terra-2026"
LOG_FILE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\local_server\server.log"
MAX_TIMEOUT = 3600  # 上限1時間
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
    """各リクエストを別スレッドで処理するHTTPサーバー。
    長時間コマンド実行中も他のリクエストを受け付け続ける。"""
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
        # localhost以外は拒否
        if self.client_address[0] not in ("127.0.0.1", "::1"):
            self.send_json(403, {"error": "forbidden: localhost only"})
            return

        # 認証チェック
        if not self.check_auth():
            self.send_json(401, {"error": "unauthorized: invalid token"})
            return

        # ボディ読み込み
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            req = json.loads(body)
        except json.JSONDecodeError:
            self.send_json(400, {"error": "invalid JSON"})
            return

        path = self.path

        # ========== /run : コマンド実行 ==========
        if path == "/run":
            cmd = req.get("cmd", "")
            cwd = req.get("cwd", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
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

        # ========== /write_and_run : ファイル書き込み → 実行 ==========
        elif path == "/write_and_run":
            filepath = req.get("filepath", "")
            content = req.get("content", "")
            run_cmd = req.get("run_cmd", "")
            cwd = req.get("cwd", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
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
    logger.info(f"ジョブズ コマンドサーバー v2 起動 → localhost:{PORT}")
    logger.info(f"ThreadingHTTPServer: 有効（並列リクエスト対応）")
    logger.info(f"最大timeout: {MAX_TIMEOUT}秒")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), CommandHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("サーバー停止")
        server.shutdown()


if __name__ == "__main__":
    run()

```

## local_server/mcp_bridge.py

```py
"""
ジョブズ用 コマンド実行MCPサーバー
Claude Desktop から使えるMCPツールとして command_server.py に橋渡しする

設定: claude_desktop_config.json に追加が必要
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
            description="ローカルPCでターミナルコマンドを実行する。Python/bat/pip/git/node等なんでも実行可能。",
            inputSchema={
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "実行するコマンド（例: python script.py, pip install requests, git push）"},
                    "cwd": {"type": "string", "description": "実行ディレクトリ（省略時はses_work）"},
                    "timeout": {"type": "integer", "description": "タイムアウト秒数（デフォルト60）"},
                },
                "required": ["cmd"],
            },
        ),
        types.Tool(
            name="write_and_run",
            description="ファイルを書き込んでから即実行する。スクリプト作成→実行を1ステップで完結。",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "書き込み先のフルパス"},
                    "content": {"type": "string", "description": "ファイルの内容"},
                    "run_cmd": {"type": "string", "description": "書き込み後に実行するコマンド（省略可）"},
                    "cwd": {"type": "string", "description": "実行ディレクトリ（省略時はses_work）"},
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
Claude Desktopからメール送信・受信確認ができるMCPサーバー
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

# Windows stdout/stdinをUTF-8に強制
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
        return {"success": False, "error": f"アカウント '{account_name}' が見つかりません"}
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
            "message": f"送信完了: {to} へ「{subject}」を送信しました",
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
        return {"success": False, "error": f"アカウント '{account_name}' が見つかりません"}
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
                        "description": "メールを送信する。松野または岡本のアカウントから送信可能。",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "account": {"type": "string", "description": "'matsuno'(松野アドレス) / 'okamoto'(岡本アドレス) / 'sessales'(TERRA共通)"},
                                "to": {"type": "string", "description": "送信先メールアドレス"},
                                "subject": {"type": "string", "description": "件名"},
                                "body": {"type": "string", "description": "本文"}
                            },
                            "required": ["account", "to", "subject", "body"]
                        }
                    },
                    {
                        "name": "get_recent_emails",
                        "description": "最新のメール一覧を取得する",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "account": {"type": "string", "description": "'matsuno'(松野アドレス) / 'okamoto'(岡本アドレス) / 'sessales'(TERRA共通)"},
                                "limit": {"type": "integer", "description": "取得件数（デフォルト10）", "default": 10}
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
    # stderrにログ出力（デバッグ用）
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
            
            # 通知メッセージ（idなし）は応答不要
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
契約マスターExcelを正として稼働中人員の請求書をfreeeにドラフト作成。

請求ルール:
【TERRA】
  P（プロパー）: GL/FP経由以外 → 15,000円/人（税別）固定
  P（プロパー）: GL/FP経由稼働 → 請求なし
  BP: 粗利×80%
  TERRA折半: 粗利×50%
  岡本折半: 粗利×80%
【フラップテック】
  通常: 粗利×68%
  小坂折半: 粗利×48%
  岡本折半: 粗利×68%
  岡本: 粗利×68%全額払出
【グレイスライン】
  粗利×60%
"""

import os, sys, requests
from datetime import date
from dateutil.relativedelta import relativedelta
import openpyxl

# token_managerを参照（自動リフレッシュ付き）
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
from token_manager import get_headers

# ===== 設定 =====
EXCEL_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\契約マスター_v6.xlsx"
FREEE_BASE = "https://api.freee.co.jp/api/1"
COMPANY_ID = 11712776

def freee_headers():
    h = get_headers()
    h["Content-Type"] = "application/json"
    return h

def safe_int(v):
    """値を安全にintに変換。文字列や日付型はスキップ(0返却)"""
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    # 文字列・日付型はスキップ
    return 0

def is_valid_name(v):
    """氏名として有効かチェック。日付型・数値・空は除外"""
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return False
    import datetime
    if isinstance(v, (datetime.datetime, datetime.date)):
        return False
    s = str(v).strip()
    if not s or s in ("NaN", "稼働中合計"):
        return False
    # 数字だけの文字列も除外
    if s.replace("/", "").replace("-", "").isdigit():
        return False
    return True

# ===== Excel読み込み =====
def load_active_entries():
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    entries = []

    # --- TERRA ---
    # ヘッダー: 担当(0) 区分(1) ステータス(2) 氏名(3) ... 案件/上位会社(6) 単価(案件)(7) ... 仕入単価(12)
    ws = wb["TERRA"]
    rows = list(ws.iter_rows(values_only=True))
    header_row = None
    for i, row in enumerate(rows):
        if row and "担当" in str(row[0]):
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

            if "稼働中" not in status: continue
            if not is_valid_name(name): continue
            name = str(name).strip()

            is_gl_ft = any(k in case for k in ["グレイスライン", "フラップテック", "GL", "FT"])
            profit = tanka - shiire

            if kubun == "P":
                if is_gl_ft:
                    continue  # 請求なし
                seikyu = 15000
                rule   = "プロパー→15,000円固定"
            elif kubun == "BP":
                if tantou == "TERRA折半":
                    seikyu = int(profit * 0.50)
                    rule   = "TERRA折半→粗利×50%"
                elif tantou == "岡本折半":
                    seikyu = int(profit * 0.80)
                    rule   = "岡本折半→粗利×80%（岡本払出あり）"
                else:
                    seikyu = int(profit * 0.80)
                    rule   = "BP→粗利×80%"
            else:
                seikyu = 15000
                rule   = "不明→15,000円固定"

            if seikyu <= 0: continue

            entries.append({
                "partner": "株式会社TERRA",
                "name": name, "profit": profit, "seikyu": seikyu,
                "rule": rule, "source": "TERRA"
            })

    # --- フラップテック ---
    # ヘッダー: 担当(0) ステータス(1) 氏名(2) 参画時期(3) 期間(4) 案件/上位(5) 案件単価(6) 仕入単価(7)
    ws = wb["フラップテック"]
    rows = list(ws.iter_rows(values_only=True))
    header_row = None
    for i, row in enumerate(rows):
        if row and "担当" in str(row[0]) and "ステータス" in str(row[1] or ""):
            header_row = i
            break
    if header_row is not None:
        for row in rows[header_row+1:]:
            if not any(row): continue
            tantou  = str(row[0] or "").strip()
            status  = str(row[1] or "").strip()
            name    = row[2]
            tanka   = safe_int(row[6])   # 案件単価(上位から)
            shiire  = safe_int(row[7])   # 仕入単価(下位へ)

            if "稼働中" not in status: continue
            if not is_valid_name(name): continue
            name = str(name).strip()
            if tanka == 0: continue  # 単価未入力はスキップ

            profit = tanka - shiire

            if profit <= 0:
                print(f"  [SKIP] {name}: 粗利{profit:,}円（単価={tanka:,} 仕入={shiire:,}）")
                continue

            if tantou == "小坂折半":
                seikyu = int(profit * 0.48)
                rule   = "小坂折半→粗利×48%"
            elif tantou in ("岡本折半", "岡本"):
                seikyu = int(profit * 0.68)
                rule   = f"{tantou}→粗利×68%（岡本払出あり）"
            else:
                seikyu = int(profit * 0.68)
                rule   = "通常→粗利×68%"

            if seikyu <= 0: continue

            entries.append({
                "partner": "株式会社フラップテック",
                "name": name, "profit": profit, "seikyu": seikyu,
                "rule": rule, "source": "FT"
            })

    # --- グレイスライン ---
    # ヘッダー: ステータス(0) 氏名(1) 参画時期(2) 期間(3) 案件/上位(4) 案件単価(5) 仕入単価(6)
    ws = wb["グレイスライン"]
    rows = list(ws.iter_rows(values_only=True))
    header_row = None
    for i, row in enumerate(rows):
        if row and "ステータス" in str(row[0]):
            header_row = i
            break
    if header_row is not None:
        for row in rows[header_row+1:]:
            if not any(row): continue
            status  = str(row[0] or "").strip()
            name    = row[1]
            tanka   = safe_int(row[5])   # 案件単価(上位から)
            shiire  = safe_int(row[6])   # 仕入単価(下位へ)

            if "稼働中" not in status: continue
            if not is_valid_name(name): continue
            name = str(name).strip()
            if tanka == 0: continue

            profit = tanka - shiire

            if profit <= 0:
                print(f"  [SKIP] {name}: 粗利{profit:,}円（単価={tanka:,} 仕入={shiire:,}）")
                continue

            seikyu = int(profit * 0.60)
            if seikyu <= 0: continue

            entries.append({
                "partner": "グレイスライン株式会社",
                "name": name, "profit": profit, "seikyu": seikyu,
                "rule": "GL→粗利×60%", "source": "GL"
            })

    return entries

# ===== freee: 取引先取得/作成 =====
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

# ===== freee: 請求書ドラフト作成 =====
def create_invoice(entry, issue_date, due_date):
    partner_id = get_or_create_partner(entry["partner"])
    mon = f"{issue_date.year}年{issue_date.month}月"
    payload = {
        "company_id": COMPANY_ID,
        "issue_date":  issue_date.strftime("%Y-%m-%d"),
        "due_date":    due_date.strftime("%Y-%m-%d"),
        "partner_id":  partner_id,
        "invoice_status": "draft",
        "title": f"{mon}分 業務委託料（{entry['name']}様）",
        "description": f"[{entry['rule']}] 粗利: {entry['profit']:,}円",
        "invoice_lines": [{
            "name":       f"業務委託料（{entry['name']}様）{mon}分",
            "quantity":   1,
            "unit_price": entry["seikyu"],
            "tax_code":   1,
            "type":       "normal"
        }]
    }
    res = requests.post(f"{FREEE_BASE}/invoices", headers=freee_headers(), json=payload)
    if res.status_code in (200, 201):
        inv_id = res.json()["invoice"]["id"]
        print(f"  OK {entry['name']} / {entry['partner']} / {entry['seikyu']:,}円 [{entry['rule']}] -> ID:{inv_id}")
        return True
    else:
        print(f"  NG {entry['name']} / {res.status_code}: {res.text[:200]}")
        return False

# ===== メイン =====
def run(target_month=None):
    today = date.today()
    if target_month is None:
        target_month = (today.replace(day=1) + relativedelta(months=1))
    issue_date = target_month.replace(day=1)
    due_date   = issue_date + relativedelta(months=1) - relativedelta(days=1)

    print(f"=== freee請求書自動生成 v2 ===")
    print(f"請求対象月: {target_month.year}年{target_month.month}月分")
    print(f"請求日: {issue_date}  支払期限: {due_date}")
    print()

    entries = load_active_entries()
    print(f"対象人員: {len(entries)}名")
    for e in entries:
        print(f"  {e['source']} | {e['name']} | 粗利{e['profit']:,}円 | 請求{e['seikyu']:,}円 | {e['rule']}")
    print()

    ok = ng = 0
    for e in entries:
        if create_invoice(e, issue_date, due_date): ok += 1
        else: ng += 1

    print()
    print(f"=== 完了: 作成{ok}件 / エラー{ng}件 ===")
    print(f"-> https://secure.freee.co.jp/invoices")
    # ===== 請求書作成完了後: 契約マスターのステータスを自動更新 =====
    if ok > 0:
        try:
            import sys as _sys2
            import os as _os2
            _sys2.path.insert(0, _os2.path.dirname(__file__))
            from auto_status_update import update_status_after_invoice
            invoiced_names = [e["name"] for e in entries]
            print(f"\n[auto_status] 請求書作成済み人員のステータスを稼働中に更新...")
            update_status_after_invoice(names=invoiced_names)
        except Exception as _e:
            print(f"[auto_status] ステータス更新スキップ（エラー: {_e}）")

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
freee トークン管理モジュール
- access_tokenは6時間で期限切れ → refresh_tokenで自動更新
- このモジュールをimportするだけでトークン管理が完結
"""
import json, time, requests, os

CLIENT_ID     = "731109064351970"
CLIENT_SECRET = "6rbUbEgQ1i58C7O6Ndg8TQDDQcoO6w9EGkCt_HkWADe9klxnGoN1iNd-vlF0vqkqdVOJYi8nfkYNY9M9evkBJQ"
TOKEN_FILE    = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\freee_token.json"
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
        print("[TOKEN] リフレッシュ成功")
        return new_data["access_token"]
    else:
        raise Exception(f"Token refresh failed: {res.text}")

def get_access_token():
    """有効なaccess_tokenを返す（期限切れなら自動リフレッシュ）"""
    token_data = load_token()
    saved_at = token_data.get("saved_at", 0)
    expires_in = token_data.get("expires_in", 21600)
    elapsed = int(time.time()) - saved_at
    
    if elapsed > (expires_in - 300):  # 5分前にリフレッシュ
        print(f"[TOKEN] 期限切れ({elapsed}秒経過) → リフレッシュ")
        return refresh_access_token()
    
    return token_data["access_token"]

def get_headers():
    return {"Authorization": f"Bearer {get_access_token()}"}

if __name__ == "__main__":
    # テスト実行
    token = get_access_token()
    print(f"[OK] access_token取得: {token[:20]}...")
    
    # APIテスト
    res = requests.get(
        f"https://api.freee.co.jp/api/1/companies",
        headers=get_headers()
    )
    print(f"[OK] API接続: {res.status_code}")
    for c in res.json().get("companies", []):
        print(f"     事業所: {c.get('display_name')} (ID: {c.get('id')})")

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
    "SES企業 東京 メールアドレス site:*.co.jp",
    "SIer 東京 採用 contact site:*.co.jp",
    "システム開発 受託 東京 問い合わせ site:*.co.jp",
    "SES派遣 IT企業 関東 mail",
    "フリーランスエンジニア 紹介 SES 東京",
]
FALLBACK_DOMAINS = {
    "SES企業 東京 メールアドレス site:*.co.jp": [
        "https://www.techbrain.co.jp",
        "https://www.mst-inc.co.jp",
        "https://www.brainets.co.jp",
    ],
    "SIer 東京 採用 contact site:*.co.jp": [
        "https://www.nsw.co.jp",
        "https://www.tis.co.jp",
    ],
    "システム開発 受託 東京 問い合わせ site:*.co.jp": [
        "https://www.nttdata.co.jp",
        "https://www.hitachi-solutions.co.jp",
    ],
    "SES派遣 IT企業 関東 mail": [
        "https://www.isg.co.jp",
        "https://www.fsi.co.jp",
    ],
    "フリーランスエンジニア 紹介 SES 東京": [
        "https://www.techbrain.co.jp",
        "https://www.brainets.co.jp",
    ],
}
KNOWN_COMPANY_NAMES = {
    "www.techbrain.co.jp": "テックブレーン株式会社",
    "www.mst-inc.co.jp": "エム・エス・ティー株式会社",
    "www.brainets.co.jp": "株式会社ブレインズ",
    "www.isg.co.jp": "株式会社ISG",
    "www.fsi.co.jp": "富士ソフト株式会社",
    "www.nsw.co.jp": "NSW株式会社",
    "www.tis.co.jp": "TIS株式会社",
    "www.nttdata.co.jp": "株式会社NTTデータ",
    "www.hitachi-solutions.co.jp": "株式会社日立ソリューションズ",
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
        print(f"取得エラー: {url} ({exc})")
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
    print(f"Google検索結果を抽出できないためフォールバック候補を使用: {query}")
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
    for separator in ["｜", "|", " - ", " – ", " — ", "／", "/"]:
        if separator in cleaned:
            cleaned = cleaned.split(separator)[0].strip()
    return cleaned


def judge_company_type(site_url: str, html: str) -> str:
    text = f"{site_url}\n{BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)}"
    if any(keyword in text for keyword in ["SES", "ses", "派遣", "技術者派遣"]):
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
    parser = argparse.ArgumentParser(description="IT・SES企業の連絡先を収集してtargets.csvへ追記します。")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="収集結果を表示し、CSVには書き込みません。")
    mode.add_argument("--run", action="store_true", help="収集結果をtargets.csvへ追記します。")
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
    print(f"追加{result['added_count']}社 / スキップ{result['skipped_duplicate_count']}社（重複）")
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
echo [%date% %time%] マッチング開始 >> "%LOG_PATH%"
python matching_v2\matching_v2.py >> "%LOG_PATH%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] マッチング完了 >> "%LOG_PATH%"
) else (
    echo [%date% %time%] マッチング失敗 >> "%LOG_PATH%"
)
echo [%date% %time%] 完了 >> "%LOG_PATH%"

```

## AGENTS.md

```md
# AGENTS.md - Codex指示書
最終更新: 2026-05-21

## 役割
あなたはエンジニア担当です。ジョブズ（Claude Desktop）から
タスクを受け取り、コードを実装して報告します。

## 担当領域

### やること
- Pythonスクリプト新規作成・修正・バグ修正
- HTML/CSS/JS・Playwright自動化スクリプト
- バッチ処理・ファイル変換・テスト実行
- ジョブズが書いた設計・仕様のコード化

### やらないこと
- Notion DBへの直接書き込み（ジョブズが行う）
- メール送信の判断・実行（ジョブズが行う）
- 事業判断・優先順位付け

## 作業ルール
- 作業ディレクトリ: C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ 配下のみ
- 文字コード: UTF-8を常に明示
- APIキーはハードコードしない（freee_token.json / config_source.json から読み込む）
- 既存の認証ファイル構成を維持する（freee_token.json / config_source.json を継続利用）
- 認証方式変更禁止
- 指示されていない全体リファクタ禁止
- import整理禁止（明示的に指示された場合のみ）
- 既存ログ削除禁止
- 関数名変更時は理由を事前報告
- 新規依存追加禁止（明示的に許可された場合のみ）
- requirements.txt を勝手に変更禁止
- 変更ファイルは最大3件。4件以上になる場合は事前報告してから実行
- 新規コード作成時は動作確認コマンドも提示

## 完了報告フォーマット
```
## 完了報告
- 作成/変更ファイル: [パス]
- 変更概要: [1〜3行]
- テスト結果: [pass/fail + 出力サマリ]
- 注意点: [あれば]
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
    contact_name = target["contact_name"] or "ご担当者"
    target_type = target["type"]
    sender_name = SENDER_NAME or "松野"
    sender_name_with_family = f"松野 {SENDER_NAME}".rstrip()

    if target_type == "元請け":
        subject = "エンジニアリングリソースのご提案"
        template = "A"
        body = f"""{contact_name}様

お世話になっております。株式会社TERRA 松野と申します。

SESエンジニアのご提案にてご連絡させていただきました。
Java/Python/インフラ等、幅広いスキルセットのエンジニアを
即日〜ご提案可能です。

ご興味がございましたら、お気軽にご返信ください。

株式会社TERRA
{sender_name_with_family}
{OUTREACH_FROM_EMAIL}
"""
        return subject, body, template

    subject = "エンジニア情報交換・BP提携のご相談"
    template = "B"
    body = f"""{contact_name}様

お世話になっております。株式会社TERRA 松野と申します。

弊社はSES事業を展開しており、BP様との情報交換・相互提案を
積極的に進めております。

案件・人員情報の交換等、ご興味がございましたら
ぜひお気軽にご返信ください。

株式会社TERRA
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

        if "断り" in memo:
            skipped += 1
            details.append(make_detail(target, "skip_断り"))
            print(f"[skip_断り] {company} <{email}>")
            continue

        if not email:
            skipped += 1
            details.append(make_detail(target, "skip_emailなし"))
            print(f"[skip_emailなし] {company}")
            continue

        if was_sent_recently(email, history, now):
            skipped += 1
            details.append(make_detail(target, "skip_180日未満"))
            print(f"[skip_180日未満] {company} <{email}>")
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
    mode.add_argument("--dry-run", action="store_true", help="送信せずログのみ出力します")
    mode.add_argument("--run", action="store_true", help="本番送信します")
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


ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
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
    parser = argparse.ArgumentParser(description="Phase1 営業パイプライン")
    parser.add_argument("--dry-run", action="store_true", help="メール送信と外部取得をスキップ")
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
        print(f"[pipeline] エラー: {exc}", flush=True)
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
        print(f"[Step2] 送信対象: {to} / {subject}", flush=True)
        entry = {"step": "intent", "path": str(path), "to": to, "subject": subject, "dry_run": dry_run, "at": datetime.now().isoformat()}
        if dry_run:
            entry["status"] = "skipped"
            print("[Step2] dry-run: メール送信スキップ", flush=True)
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
                print(f"[Step2] 送信エラー: {exc}", flush=True)
        _append_log(entry)
        results.append(entry)
    if not results and dry_run:
        print("[Step2] dry-run: メール送信スキップ", flush=True)
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
            print(f"[Step3] メール取得エラー({path}): {exc}", flush=True)
    return []


def _parse_skill_marks(body: str, title: str) -> dict:
    found = {}
    capture = False
    for line in body.splitlines():
        if title in line:
            capture = True
            continue
        if capture and line.startswith("▼"):
            break
        if capture:
            m = re.search(r"[・\-]?\s*([^:：]+)\s*[:：]\s*([○◯×xX])", line)
            if m:
                found[m.group(1).strip()] = "×" if m.group(2).lower() in {"×", "x"} else "○"
    return found


def parse_reply(email_item: dict) -> dict:
    body = email_item.get("body") or email_item.get("body_preview") or ""
    statuses = []
    for line in body.splitlines():
        if any(word in line for word in ("面談調整中", "面談予定", "結果待ち", "オファー中")):
            statuses.append(line.strip(" ・\t"))
    return {
        "mail_id": str(email_item.get("id") or email_item.get("message_id") or "unknown"),
        "subject": email_item.get("subject", ""),
        "from": email_item.get("from", ""),
        "parallel_status": statuses,
        "required_skills": _parse_skill_marks(body, "必須"),
        "preferred_skills": _parse_skill_marks(body, "尚可"),
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
    print(f"[Step3] 未読メール確認: {len(parsed)}件", flush=True)
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
        print(f"[Step5] result.json読込エラー: {exc}", flush=True)
    return []


def _skill_summary(value) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{k}:{v.get('result', v)}" if isinstance(v, dict) else f"{k}:{v}" for k, v in value.items()) or "確認中"
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
            blocks.append(CANDIDATE_TEMPLATE.format(
                rank_label=labels[idx],
                name=candidate.get("engineer_name") or candidate.get("name") or "候補者",
                price=candidate.get("proposed_price") or candidate.get("price") or "確認中",
                available_date=candidate.get("available_date") or "確認中",
                required=_skill_summary(candidate.get("required") or candidate.get("required_match")),
                preferred=_skill_summary(candidate.get("optional") or candidate.get("preferred_match")),
                appeal=f"マッチングスコア {candidate.get('score', '確認中')}",
            ))
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
        print(f"[Step6] 送信対象: {to} / {subject}", flush=True)
        entry = {"step": "proposal", "path": str(path), "to": to, "subject": subject, "dry_run": dry_run, "at": datetime.now().isoformat()}
        if dry_run:
            entry["status"] = "skipped"
            print("[Step6] dry-run: 提案メール送信スキップ", flush=True)
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
                print(f"[Step6] 送信エラー: {exc}", flush=True)
        _append_log(entry)
        results.append(entry)
    if not results and dry_run:
        print("[Step6] dry-run: 提案メール送信スキップ", flush=True)
    return results


if __name__ == "__main__":
    send_proposals(dry_run=True)

```

## sales_pipeline/templates.py

```py
from __future__ import annotations


IKOUKAKUNIN_SUBJECT = "{candidate_name}様 案件ご検討のお願い（{role_area}）"

IKOUKAKUNIN_TEMPLATE = """{affiliation} {contact_name}様

いつもお世話になっております。

人員のご紹介ありがとうございます。
下記案件いかがでしょうか。
ご検討いただけますと幸いです。

また、エントリーいただける場合下記2点ご教授いただけますと幸いです。
・並行状況
・必須、尚可の○×

━━━━━━━━━━━━━━━━━━
■ 案件概要
━━━━━━━━━━━━━━━━━━
案件名    : {project_name}
業務内容  : {description}
必須スキル: {required_skills}
尚可スキル: {preferred_skills}
単価      : {proposed_price}万円
期間      : {period}
勤務地    : {location}（リモート可否: {remote}）
面談      : {interview_count}回
外国籍    : {foreign_ok}

━━━━━━━━━━━━━━━━━━
■ ご記入フォーマット
━━━━━━━━━━━━━━━━━━
▼必須スキル（○/×）
{required_format}
▼尚可スキル（○/×）
{preferred_format}

▼並行状況
 例）
  ・A社: 面談調整中
  ・B社: 面談予定 2/2（○月○日）
  ・C社: 結果待ち 2/2（面談実施日 ○月○日）

何卒よろしくお願いいたします。
"""

PROPOSAL_SUBJECT = "{project_name} ご提案"

PROPOSAL_TEMPLATE = """ご担当者様

いつもお世話になっております。
下記の通り、候補者をご提案いたします。

━━━━━━━━━━━━━━━━━━
■ 案件
━━━━━━━━━━━━━━━━━━
{project_name}

━━━━━━━━━━━━━━━━━━
■ ご提案候補者
━━━━━━━━━━━━━━━━━━
{candidate_blocks}

━━━━━━━━━━━━━━━━━━
■ サマリー
━━━━━━━━━━━━━━━━━━
{summary}

ご確認のほど、何卒よろしくお願いいたします。
"""

CANDIDATE_TEMPLATE = """【{rank_label}】{name}
単価: {price}万円
稼働開始: {available_date}
必須スキル: {required}
尚可スキル: {preferred}
補足: {appeal}
"""


def skill_format(skills: list[str]) -> str:
    if not skills:
        return "・特になし"
    return "\n".join(f"・{skill}: " for skill in skills)

```

## mail_pipeline/mail_pipeline.py

```py
"""
mail_pipeline.py - v5.1
v4からの変更:
- 人材メール受信時: 添付スキルシート（PDF/Word/画像）を自動検出
- skill_readerでスキル抽出 → 案件照合 → 粗利ジャスト意向確認文生成
- 添付なし場合はメール本文からスキル抽出（従来通り）
- 案件登録時もskill_readerのget_active_projects/match_skillsを利用
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

# skill_readerをインポート
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from skill_reader.skill_reader import (
    extract_skills_from_text, extract_skills_from_image,
    extract_text_from_pdf, extract_text_from_docx, pdf_to_base64_image,
    get_active_projects, match_skills, generate_iko_mail
)
from usage_tracker.cost_logger import log_cost

# ===== 設定 =====
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
    "React", "AWS", "インフラ", "Go", "Ruby", "Swift", "Kotlin", "Vue.js",
    "Angular", "Docker", "Kubernetes", "GCP", "Azure", "Spring",
    "MySQL", "PostgreSQL", "Oracle", "MongoDB", "Linux"
]

DOUBLE_CHECK_SYSTEM = f"""あなたはSES業界のダブルチェック専門AIです。
提案文と候補者情報を受け取り、以下のルールで厳密にチェックしてください。

今日の日付: {date.today().isoformat()}

【1. 除外ルール違反】
- 外国籍人材が含まれていないか
- 地方在住（関東以外）が含まれていないか
- 短期案件連続の人材が含まれていないか
- ブランクがある人材が含まれていないか
- 既往歴がある人材が含まれていないか

【2. 単価チェック（粗利）】
- 粗利 = 案件単価 - エンジニア単価
- 粗利5万円未満はNG / 粗利7万円以上が目標

【3. 並行スコア】
- 面談調整中:1.5 / 面談予定:2.0 / 結果待ち1-2日:2.5 / 3-7日:2.0 / 8-14日:1.5 / 15日超:1.0 / オファー中:5.0
- 合計5.0以上はNG

【4. 敬語・表現チェック】
- 「充足」→「全て満たしており」
- 「即戦力です」→「マッチ度高い人員かと存じます」

【5. 固有名詞マスキング】
- 企業名・担当者名・連絡先が残っていないか

出力フォーマット:
【判定】OK / NG
【チェック結果】
1. 除外ルール: OK/NG（理由）
2. 単価・粗利: OK/NG（詳細）
3. 並行スコア: OK/NG（詳細）
4. 敬語表現: OK/NG（修正箇所）
5. マスキング: OK/NG（漏れ箇所）
【修正済み提案文】
NGの場合は修正した提案文、OKの場合は「修正不要」
【所見】
気になる点があれば一言"""


# ===== ログ =====
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
    """IMAPログインアカウントから入力元ラベルを返す"""
    if "r-matsuno" in (email_user or ""):
        return "松野メール"
    if "r-okamoto" in (email_user or ""):
        return "岡本メール"
    return "共通メール"


# ===== 処理済みID管理 =====
def load_processed_ids() -> set:
    try:
        if PROCESSED_IDS_PATH.exists():
            with open(PROCESSED_IDS_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except Exception as e:
        log(f"processed_ids読み込みエラー: {e}")
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
        log(f"processed_ids保存エラー: {e}")


# ===== メール取得（添付ファイル対応 v5新規）=====
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
    """本文テキストと添付スキルシート（バイナリ+MIMEタイプ）を取得"""
    body = ""
    attachments = []  # [{"data": bytes, "mime": str, "filename": str}]

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition  = str(part.get("Content-Disposition", ""))
        filename_raw = part.get_filename()
        filename     = decode_str(filename_raw) if filename_raw else ""

        # 本文テキスト
        if content_type == "text/plain" and "attachment" not in disposition:
            charset = part.get_content_charset() or "utf-8"
            try:
                body = part.get_payload(decode=True).decode(charset, errors="replace")
            except Exception:
                pass
            continue

        # 添付ファイル判定
        ext = Path(filename).suffix.lower() if filename else ""
        is_skill_sheet = (
            content_type in SKILL_SHEET_MIME_TYPES or
            ext in SKILL_SHEET_EXTENSIONS
        )

        if is_skill_sheet and ("attachment" in disposition or filename):
            data = part.get_payload(decode=True)
            if data:
                # MIMEタイプを正規化
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
                log(f"    添付検出: {filename} ({mime}) {len(data)}bytes")

    return body.strip(), attachments


def fetch_recent_emails(limit: int = 50):
    log(f"IMAP接続開始（直近{limit}件取得）")
    ctx = ssl.create_default_context()
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=ctx)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")
    except Exception as e:
        log(f"IMAP接続エラー: {e}")
        return []

    status, messages = mail.search(None, "ALL")
    if status != "OK" or not messages[0]:
        log("対象メールなし")
        mail.logout()
        return []

    all_ids = messages[0].split()
    target_ids = list(reversed(all_ids[-limit:]))
    log(f"全件数: {len(all_ids)}件 → 直近{len(target_ids)}件を処理対象")

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
                "attachments": attachments  # v5追加
            })
        except Exception as e:
            log(f"メール取得エラー: {e}")

    mail.logout()
    log(f"取得完了: {len(emails)}件")
    return emails


# ===== スキルフィルタリング =====
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
        log(f"Claude APIエラー: {res.status_code} {res.text[:200]}")
        return ""
    except Exception as e:
        log(f"Claude呼び出し例外: {e}")
        return ""


def classify_email(subject: str, body: str) -> dict:
    system = """あなたはSES業界の情報解析AIです。メールを解析してJSON形式のみで返答してください。

案件情報の場合:
{"type":"project","name":"案件名","required_skills":["Java"],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"不明","period":"","interview_count":1,"foreign_ok":false,"note":"業務内容"}

人材情報の場合:
{"type":"engineer","name":"氏名","skills":["Java"],"price":0,"available_date":"","experience_years":0,"company":"","note":"備考"}

どちらでもない場合:
{"type":"other","note":"内容要約"}"""
    text = f"件名: {subject}\n\n{body[:2000]}"
    result = call_claude(system, text)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        parsed = json.loads(clean)
        return parsed if isinstance(parsed, dict) else {"type": "other", "note": "予期しない形式"}
    except:
        return {"type": "other", "note": "解析失敗"}


def extract_affiliation(body: str) -> str:
    """メール本文から所属会社名を抽出。取れなければ空文字。"""
    if not ANTHROPIC_KEY or not body:
        return ""
    system = 'メール本文から送信元または紹介元の所属会社名だけを抽出し、JSONのみで返してください。形式: {"company":""}'
    result = call_claude(system, body[:2000], max_tokens=120)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        parsed = json.loads(clean)
        company = str(parsed.get("company", "")).strip() if isinstance(parsed, dict) else ""
        return company[:30]
    except Exception:
        return ""


def ai_matching(project: dict, engineers: list) -> dict:
    system = """あなたはSES業界のマッチングAIです。JSONで返してください。

除外ルール:
- 必須スキルに✕ → 除外
- 単価乖離5万超 → 除外

サマリー文（禁止: 充足・即戦力です）:
- 必須全○+尚可全○ → "必須・尚可ともにマッチ度高い人員"
- 必須全○+尚可○率50%以上 → "必須全て満たしており、尚可も○項目経験あり"
- 必須全○のみ → "必須スキル全て満たし即稼働可能"

返答フォーマット:
{"candidates":[{"name":"氏名","price":0,"summary":"サマリー","required_match":{},"optional_match":{},"parallel":"なし"}],"proposal_draft":"提案メール本文"}"""
    payload = {"project": project, "engineers": engineers}
    result = call_claude(system, json.dumps(payload, ensure_ascii=False), max_tokens=2000)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        return json.loads(clean)
    except:
        return {"candidates": [], "proposal_draft": ""}


def double_check(text: str) -> str:
    return call_claude(DOUBLE_CHECK_SYSTEM, text, max_tokens=2000)


# ===== Notion操作 =====
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
                log(f"Notion DBプロパティ取得スキップ: {res.status_code} {res.text[:120]}")
                DB_PROPERTY_CACHE[db_id] = set()
        except Exception as e:
            log(f"Notion DBプロパティ取得例外: {e}")
            DB_PROPERTY_CACHE[db_id] = set()
    return DB_PROPERTY_CACHE[db_id]


def add_input_source_properties(properties: dict, db_id: str, input_source: str, affiliation: str):
    prop_names = get_database_property_names(db_id)
    if input_source and "入力元" in prop_names:
        properties["入力元"] = {"select": {"name": input_source}}
    if affiliation and "所属会社名" in prop_names:
        properties["所属会社名"] = {"rich_text": [{"text": {"content": affiliation[:500]}}]}


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
    name = info.get("name") or f"【{subject[:20]}】"
    note = f"【メールから自動登録】\n送信者: {sender}\n件名: {subject}\n\n{info.get('note','')}"
    properties = {
        "案件名": {"title": [{"text": {"content": name}}]},
        "ステータス": {"select": {"name": "募集中"}},
        "案件詳細": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req:
        properties["必要スキル"] = {"multi_select": [{"name": s} for s in req]}
    if opt:
        properties["尚可スキル"] = {"multi_select": [{"name": s} for s in opt]}
    if info.get("price"):
        properties["単価（万円）"] = {"number": info["price"]}
    if is_valid_iso_date(info.get("start_date")):
        properties["開始日"] = {"date": {"start": info["start_date"].strip()}}
    if info.get("location"):
        properties["勤務地"] = {"rich_text": [{"text": {"content": info["location"]}}]}
    add_input_source_properties(properties, PROJECT_DB, input_source, affiliation)
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": PROJECT_DB}, "properties": properties}
    )
    return res.status_code == 200


def register_engineer(info: dict, subject: str, sender: str, input_source: str = "", affiliation: str = "") -> tuple:
    """エンジニア登録、NotionページIDも返す"""
    name = info.get("name") or "（名前未記載）"
    note = f"【メールから自動登録】\n送信者: {sender}\n件名: {subject}\n\n{info.get('note','')}"
    properties = {
        "名前": {"title": [{"text": {"content": name}}]},
        "稼働状況": {"select": {"name": "稼働可能"}},
        "備考（LINEメモ）": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    skills = [s for s in info.get("skills", []) if s in VALID_SKILLS]
    if skills:
        properties["スキル"] = {"multi_select": [{"name": s} for s in skills]}
    if info.get("price"):
        properties["単価（万円）"] = {"number": info["price"]}
    if is_valid_iso_date(info.get("available_date")):
        properties["稼働可能日"] = {"date": {"start": info["available_date"].strip()}}
    if info.get("experience_years"):
        properties["経験年数"] = {"number": info["experience_years"]}
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
        "property": "稼働状況", "select": {"equals": "稼働可能"}
    })
    engineers = []
    for p in pages:
        props = p["properties"]
        name_prop = props.get("名前", {}).get("title", [])
        name   = name_prop[0]["plain_text"] if name_prop else "未記載"
        skills = [o["name"] for o in props.get("スキル", {}).get("multi_select", [])]
        price  = props.get("単価（万円）", {}).get("number", 0) or 0
        avail  = (props.get("稼働可能日", {}).get("date") or {}).get("start", "")
        note_prop = props.get("備考（LINEメモ）", {}).get("rich_text", [])
        note   = note_prop[0]["plain_text"][:200] if note_prop else ""
        engineers.append({"name": name, "skills": skills, "price": price,
                          "available_date": avail, "note": note})
    return engineers


# ===== スキルシート処理（v5新規）=====
def process_skill_sheet(attachment: dict, engineer_price: int = None,
                        affiliation: str = "貴社") -> dict | None:
    """
    添付スキルシートを処理してスキル抽出・案件照合・意向確認文を生成する。
    Returns: {"info": dict, "match_results": list, "iko_mail": str} or None
    """
    data = attachment["data"]
    mime = attachment["mime"]
    fname = attachment["filename"]

    log(f"    スキルシート処理中: {fname}")
    info = None

    try:
        if mime == "application/pdf":
            text = extract_text_from_pdf(data)
            if text:
                info = extract_skills_from_text(text)
            else:
                log("    (テキストなし → 画像変換)")
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
        log(f"    スキルシート処理エラー: {e}")
        return None

    if not info:
        log("    スキル抽出失敗")
        return None

    log(f"    抽出スキル: {', '.join(info.get('skills', []))}")

    # 案件照合
    projects = get_active_projects()
    match_results = match_skills(info.get("skills", []), projects, engineer_price)

    # 意向確認メール生成
    iko_mail = generate_iko_mail(info, match_results, engineer_price, affiliation)

    just_count = sum(1 for r in match_results
                     if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12)
    log(f"    照合完了: 提案可{sum(1 for r in match_results if r['proposable'])}件 "
        f"(粗利ジャスト{just_count}件)")

    return {"info": info, "match_results": match_results, "iko_mail": iko_mail}


# ===== 下書き保存 =====
def save_draft(proj_name: str, reply_to: str, candidates: list,
               check_result: str, final_proposal: str,
               skill_result: dict = None):
    DRAFTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', proj_name)[:30]
    path = DRAFTS_DIR / f"{ts}_{safe_name}.txt"

    is_ok = "【判定】OK" in check_result

    content = f"""================================================================
提案文下書き v5
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================
【案件名】{proj_name}
【返信先】{reply_to}

【候補者】
"""
    for i, c in enumerate(candidates[:3], 1):
        content += f"  {'①②③'[i-1]} {c['name']} / {c.get('price',0)}万円\n"
        content += f"     {c.get('summary','')}\n"

    content += f"""
【ダブルチェック結果】
判定: {'[OK]' if is_ok else '[NG]'}
{check_result[:800]}

【提案メール本文（送信可能版）】
{final_proposal}
================================================================
"""

    # v5: スキルシート照合結果も付記
    if skill_result:
        just = [r for r in skill_result["match_results"]
                if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12]
        content += f"""
【スキルシート照合結果（skill_reader）】
氏名: {skill_result['info'].get('name', '不明')}
スキル: {', '.join(skill_result['info'].get('skills', []))}
レベル: {skill_result['info'].get('level', '不明')}

粗利ジャスト案件TOP:
"""
        for r in just[:3]:
            content += f"  {r['project_name']} | 粗利{r['gross']}万\n"

        content += f"""
【意向確認メール文面】
{skill_result['iko_mail']}
================================================================
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def save_engineer_draft(engineer_info: dict, match_results: list,
                        iko_mail: str, reply_to: str, sender: str):
    """人材メール専用の下書き保存"""
    DRAFTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = engineer_info.get("name", "不明")
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', name)[:20]
    path = DRAFTS_DIR / f"{ts}_engineer_{safe_name}.txt"

    just = [r for r in match_results
            if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12]

    content = f"""================================================================
人材メール処理結果 v5
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================
【エンジニア】{name}
【送信者】{sender}
【返信先】{reply_to}

【抽出スキル】{', '.join(engineer_info.get('skills', []))}
【レベル推定】{engineer_info.get('level', '不明')}
【概要】{engineer_info.get('summary', '')}

【粗利ジャスト案件（5〜12万）TOP{len(just)}件】
"""
    for r in just[:5]:
        req_str = "  ".join(f"{s}:{'○' if v else '×'}" for s, v in r["required"].items()) or "なし"
        content += f"  {r['project_name']} ({r['client']}) | {r['project_price']}万 | 粗利{r['gross']}万\n"
        content += f"    必須: {req_str}\n"

    content += f"""
【意向確認メール文面（粗利ジャストTOP3）】
{iko_mail}
================================================================
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ===== メイン =====
def main():
    log("=" * 50)
    log("メールパイプライン v5.1 起動（入力元ラベル・所属会社名追加）")
    log(f"設定: 取得{FETCH_LIMIT}件 / 処理{PROCESS_LIMIT}件 / マッチング上位{MATCH_TOP_N}名")
    input_source = get_input_source_label(EMAIL_USER)
    log(f"入力元: {input_source}")

    processed = load_processed_ids()
    log(f"処理済みID: {len(processed)}件")

    emails = fetch_recent_emails(limit=FETCH_LIMIT)
    if not emails:
        log("処理対象なし・終了")
        return

    new_emails = [e for e in emails if e["msg_id"] not in processed]
    log(f"新規処理対象: {len(new_emails)}件")

    if not new_emails:
        log("全て処理済み・終了")
        return

    target_emails = new_emails[:PROCESS_LIMIT]
    engineers = get_available_engineers()
    log(f"エンジニアDB: {len(engineers)}名（稼働可能）")

    for em in target_emails:
        subject     = em["subject"]
        sender      = em["sender"]
        reply_to    = em["reply_to"]
        body        = em["body"]
        msg_id      = em["msg_id"]
        attachments = em.get("attachments", [])

        log(f"処理中: {subject[:50]}")
        if attachments:
            log(f"  添付: {len(attachments)}件")

        info = classify_email(subject, body)
        msg_type = info.get("type", "other")
        log(f"  判定: {msg_type}")

        if msg_type == "project":
            affiliation = extract_affiliation(body)
            ok = register_project(info, subject, sender, input_source, affiliation)
            proj_name = info.get("name") or subject[:30]
            if not ok:
                log(f"  [NG] 案件Notion登録失敗")
                save_processed_id(msg_id, processed)
                continue
            log(f"  [OK] 案件登録: {proj_name}")

            filtered = filter_engineers_by_skills(info, engineers, top_n=MATCH_TOP_N)
            log(f"  スキルフィルタ: {len(engineers)}名 → {len(filtered)}名")

            if not filtered:
                log(f"  [!!] 候補者なし")
                save_processed_id(msg_id, processed)
                continue

            matching = ai_matching(info, filtered)
            candidates = matching.get("candidates", [])
            proposal_draft = matching.get("proposal_draft", "")

            if not candidates:
                log(f"  [!!] AIマッチング候補なし")
                save_processed_id(msg_id, processed)
                continue
            log(f"  AIマッチング: {len(candidates)}名")

            check_input = f"【案件名】{proj_name}\n\n【提案文ドラフト】\n{proposal_draft}\n\n【候補者】\n"
            for c in candidates:
                check_input += f"- {c['name']} / {c.get('price',0)}万円 / 並行: {c.get('parallel','なし')}\n"
            check_result = double_check(check_input)

            final_proposal = proposal_draft
            marker = "【修正済み提案文】"
            if marker in check_result:
                after = check_result.split(marker, 1)[1].strip()
                if "【所見】" in after:
                    after = after.split("【所見】")[0].strip()
                if after and after != "修正不要":
                    final_proposal = after

            # 案件メールにも添付スキルシートがある場合は処理
            skill_result = None
            if attachments:
                skill_result = process_skill_sheet(
                    attachments[0],
                    engineer_price=None,
                    affiliation="貴社"
                )

            draft_path = save_draft(proj_name, reply_to, candidates,
                                    check_result, final_proposal, skill_result)
            log(f"  [OK] 提案文下書き保存: {draft_path.name}")

        elif msg_type == "engineer":
            # ===== v5: スキルシート添付対応 =====
            name = info.get("name", "（名前未記載）")
            eng_price = info.get("price") or None

            affiliation = extract_affiliation(body)
            skill_affiliation = affiliation or (sender.split("<")[0].strip() if "<" in sender else "貴社")

            skill_result = None

            # 添付スキルシートがある場合はskill_readerで処理
            if attachments:
                log(f"  添付スキルシートを処理: {attachments[0]['filename']}")
                skill_result = process_skill_sheet(
                    attachments[0],
                    engineer_price=eng_price,
                    affiliation=skill_affiliation
                )
                if skill_result:
                    # スキル抽出結果でinfo.skillsを上書き（より精度が高い）
                    info["skills"] = skill_result["info"].get("skills", info.get("skills", []))
                    log(f"  スキルシートからスキル上書き: {info['skills']}")

            # Notion登録
            ok, notion_id = register_engineer(info, subject, sender, input_source, affiliation)
            if ok:
                log(f"  [OK] 人材登録: {name} (Notion ID: {notion_id[:8]}...)")

                # skill_readerの結果があればNotionスキル欄も更新済み（register_engineerで登録）
                # 人材下書き保存
                if skill_result:
                    draft_path = save_engineer_draft(
                        skill_result["info"],
                        skill_result["match_results"],
                        skill_result["iko_mail"],
                        reply_to, sender
                    )
                    log(f"  [OK] 人材下書き保存: {draft_path.name}")
                    just = sum(1 for r in skill_result["match_results"]
                               if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12)
                    log(f"  粗利ジャスト案件: {just}件 → 意向確認文生成済み")
                else:
                    # 添付なし：本文から抽出した情報で照合のみ
                    projects = get_active_projects()
                    match_results = match_skills(info.get("skills", []), projects, eng_price)
                    iko_mail = generate_iko_mail(info, match_results, eng_price, skill_affiliation)
                    draft_path = save_engineer_draft(info, match_results, iko_mail, reply_to, sender)
                    log(f"  [OK] 本文ベース人材下書き保存: {draft_path.name}")
            else:
                log(f"  [NG] 人材Notion登録失敗: {name}")

        else:
            log(f"  スキップ（その他）: {subject[:40]}")

        save_processed_id(msg_id, processed)

    log("メールパイプライン v5.1 完了")
    log("=" * 50)


if __name__ == "__main__":
    main()

```

## mail_pipeline/mail_pipeline_test1.py

```py
"""
メールパイプライン v4
- v3からの変更: マッチング前にPython側でスキルフィルタリング（上位10名に絞り込み）
- Notionエンジニア4,642名をそのままAIに渡すとトークン超過 → Python側でフィルタリング後に渡す
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

# ===== 設定 =====
BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR.parent / "config" / ".env"
DRAFTS_DIR = BASE_DIR / "pipeline_drafts"
LOG_PATH = BASE_DIR / "pipeline.log"
PROCESSED_IDS_PATH = BASE_DIR / "processed_ids.json"

FETCH_LIMIT = 50
PROCESS_LIMIT = 1
MATCH_TOP_N = 10  # AIに渡す最大候補数

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
    "React", "AWS", "インフラ", "Go", "Ruby", "Swift", "Kotlin", "Vue.js",
    "Angular", "Docker", "Kubernetes", "GCP", "Azure", "Spring",
    "MySQL", "PostgreSQL", "Oracle", "MongoDB", "Linux"
]

DOUBLE_CHECK_SYSTEM = f"""あなたはSES業界のダブルチェック専門AIです。
提案文と候補者情報を受け取り、以下のルールで厳密にチェックしてください。

今日の日付: {date.today().isoformat()}

【1. 除外ルール違反】
- 外国籍人材が含まれていないか
- 地方在住（関東以外）が含まれていないか
- 短期案件連続の人材が含まれていないか
- ブランクがある人材が含まれていないか
- 既往歴がある人材が含まれていないか

【2. 単価チェック（粗利）】
- 粗利 = 案件単価 - エンジニア単価
- 粗利5万円未満はNG / 粗利7万円以上が目標

【3. 並行スコア】
- 面談調整中:1.5 / 面談予定:2.0 / 結果待ち1-2日:2.5 / 3-7日:2.0 / 8-14日:1.5 / 15日超:1.0 / オファー中:5.0
- 合計5.0以上はNG

【4. 敬語・表現チェック】
- 「充足」→「全て満たしており」
- 「即戦力です」→「マッチ度高い人員かと存じます」

【5. 固有名詞マスキング】
- 企業名・担当者名・連絡先が残っていないか

出力フォーマット:
【判定】OK / NG
【チェック結果】
1. 除外ルール: OK/NG（理由）
2. 単価・粗利: OK/NG（詳細）
3. 並行スコア: OK/NG（詳細）
4. 敬語表現: OK/NG（修正箇所）
5. マスキング: OK/NG（漏れ箇所）
【修正済み提案文】
NGの場合は修正した提案文、OKの場合は「修正不要」
【所見】
気になる点があれば一言"""


# ===== ログ =====
def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ===== 処理済みID管理 =====
def load_processed_ids() -> set:
    try:
        if PROCESSED_IDS_PATH.exists():
            with open(PROCESSED_IDS_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except Exception as e:
        log(f"processed_ids読み込みエラー: {e}")
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
        log(f"processed_ids保存エラー: {e}")


# ===== メール取得 =====
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
    log(f"IMAP接続開始（直近{limit}件取得）")
    ctx = ssl.create_default_context()
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=ctx)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")
    except Exception as e:
        log(f"IMAP接続エラー: {e}")
        return []

    status, messages = mail.search(None, "ALL")
    if status != "OK" or not messages[0]:
        log("対象メールなし")
        mail.logout()
        return []

    all_ids = messages[0].split()
    target_ids = list(reversed(all_ids[-limit:]))
    log(f"全件数: {len(all_ids)}件 → 直近{len(target_ids)}件を処理対象")

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
            log(f"メール取得エラー: {e}")

    mail.logout()
    log(f"取得完了: {len(emails)}件")
    return emails


# ===== スキルフィルタリング（★v4新規追加★） =====
def filter_engineers_by_skills(project: dict, engineers: list, top_n: int = MATCH_TOP_N) -> list:
    """
    案件の必須・尚可スキルでエンジニアをフィルタリングし上位top_n名を返す。
    スコア = 必須スキルマッチ数*2 + 尚可スキルマッチ数*1
    必須スキルが1つもマッチしない場合は除外。
    単価乖離5万超も除外。
    """
    required = [s.lower() for s in project.get("required_skills", [])]
    optional = [s.lower() for s in project.get("optional_skills", [])]
    proj_price = project.get("price", 0) or 0

    scored = []
    for eng in engineers:
        eng_skills = [s.lower() for s in eng.get("skills", [])]
        eng_price = eng.get("price", 0) or 0

        # 単価乖離チェック（5万超は除外）
        if proj_price > 0 and eng_price > 0:
            if abs(proj_price - eng_price) > 5:
                continue

        # 必須スキルマッチ数
        req_match = sum(1 for r in required if any(r in s for s in eng_skills))
        # 必須スキルが1つもなければ除外（必須が指定されている場合のみ）
        if required and req_match == 0:
            continue

        # 尚可スキルマッチ数
        opt_match = sum(1 for o in optional if any(o in s for s in eng_skills))

        score = req_match * 2 + opt_match
        scored.append((score, eng))

    # スコア降順でソート、上位top_n名を返す
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
        log(f"Claude APIエラー: {res.status_code} {res.text[:200]}")
        return ""
    except Exception as e:
        log(f"Claude呼び出し例外: {e}")
        return ""


def classify_email(subject: str, body: str) -> dict:
    system = """あなたはSES業界の情報解析AIです。メールを解析してJSON形式のみで返答してください。

案件情報の場合:
{"type":"project","name":"案件名","required_skills":["Java"],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"不明","period":"","interview_count":1,"foreign_ok":false,"note":"業務内容"}

人材情報の場合:
{"type":"engineer","name":"氏名","skills":["Java"],"price":0,"available_date":"","experience_years":0,"company":"","note":"備考"}

どちらでもない場合:
{"type":"other","note":"内容要約"}"""
    text = f"件名: {subject}\n\n{body[:2000]}"
    result = call_claude(system, text)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        return json.loads(clean)
    except:
        return {"type": "other", "note": "解析失敗"}


def ai_matching(project: dict, engineers: list) -> dict:
    system = """あなたはSES業界のマッチングAIです。JSONで返してください。

除外ルール:
- 必須スキルに✕ → 除外
- 単価乖離5万超 → 除外（案件単価-5万〜+2万の範囲のみ）

サマリー文（禁止: 充足・即戦力です）:
- 必須全○+尚可全○ → "必須・尚可ともにマッチ度高い人員"
- 必須全○+尚可○率50%以上 → "必須全て満たしており、尚可も○項目経験あり"
- 必須全○のみ → "必須スキル全て満たし即稼働可能"

返答フォーマット:
{"candidates":[{"name":"氏名","price":0,"summary":"サマリー","required_match":{},"optional_match":{},"parallel":"なし"}],"proposal_draft":"提案メール本文"}"""
    payload = {"project": project, "engineers": engineers}
    result = call_claude(system, json.dumps(payload, ensure_ascii=False), max_tokens=2000)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        return json.loads(clean)
    except:
        return {"candidates": [], "proposal_draft": ""}


def double_check(text: str) -> str:
    return call_claude(DOUBLE_CHECK_SYSTEM, text, max_tokens=2000)


# ===== Notion操作 =====
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
    name = info.get("name") or f"【{subject[:20]}】"
    note = f"【メールから自動登録】\n送信者: {sender}\n件名: {subject}\n\n{info.get('note','')}"
    properties = {
        "案件名": {"title": [{"text": {"content": name}}]},
        "ステータス": {"select": {"name": "募集中"}},
        "案件詳細": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req:
        properties["必要スキル"] = {"multi_select": [{"name": s} for s in req]}
    if opt:
        properties["尚可スキル"] = {"multi_select": [{"name": s} for s in opt]}
    if info.get("price"):
        properties["単価（万円）"] = {"number": info["price"]}
    if info.get("start_date"):
        properties["開始日"] = {"date": {"start": info["start_date"]}}
    if info.get("location"):
        properties["勤務地"] = {"rich_text": [{"text": {"content": info["location"]}}]}
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": PROJECT_DB}, "properties": properties}
    )
    if res.status_code != 200:
        log(f"  [Notion ERROR project] {res.status_code}: {res.text[:300]}")
    return res.status_code == 200


def register_engineer(info: dict, subject: str, sender: str) -> bool:
    name = info.get("name") or "（名前未記載）"
    note = f"【メールから自動登録】\n送信者: {sender}\n件名: {subject}\n\n{info.get('note','')}"
    properties = {
        "名前": {"title": [{"text": {"content": name}}]},
        "稼働状況": {"select": {"name": "稼働可能"}},
        "備考（LINEメモ）": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    skills = [s for s in info.get("skills", []) if s in VALID_SKILLS]
    if skills:
        properties["スキル"] = {"multi_select": [{"name": s} for s in skills]}
    if info.get("price"):
        properties["単価（万円）"] = {"number": info["price"]}
    if info.get("available_date"):
        properties["稼働可能日"] = {"date": {"start": info["available_date"]}}
    if info.get("experience_years"):
        properties["経験年数"] = {"number": info["experience_years"]}
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
        "property": "稼働状況", "select": {"equals": "稼働可能"}
    })
    engineers = []
    for p in pages:
        props = p["properties"]
        name_prop = props.get("名前", {}).get("title", [])
        name   = name_prop[0]["plain_text"] if name_prop else "未記載"
        skills = [o["name"] for o in props.get("スキル", {}).get("multi_select", [])]
        price  = props.get("単価（万円）", {}).get("number", 0) or 0
        avail  = (props.get("稼働可能日", {}).get("date") or {}).get("start", "")
        note_prop = props.get("備考（LINEメモ）", {}).get("rich_text", [])
        note   = note_prop[0]["plain_text"][:200] if note_prop else ""
        engineers.append({"name": name, "skills": skills, "price": price,
                          "available_date": avail, "note": note})
    return engineers


# ===== 提案文下書き保存 =====
def save_draft(proj_name: str, reply_to: str, candidates: list,
               check_result: str, final_proposal: str):
    DRAFTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', proj_name)[:30]
    path = DRAFTS_DIR / f"{ts}_{safe_name}.txt"

    is_ok = "【判定】OK" in check_result or "判定】OK" in check_result

    content = f"""================================================================
提案文下書き
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================
【案件名】{proj_name}
【返信先】{reply_to}

【候補者】
"""
    for i, c in enumerate(candidates[:3], 1):
        content += f"  {'①②③'[i-1]} {c['name']} / {c.get('price',0)}万円\n"
        content += f"     {c.get('summary','')}\n"

    content += f"""
【ダブルチェック結果】
判定: {'[OK] OK' if is_ok else '[NG] NG'}
{check_result[:800]}

【提案メール本文（送信可能版）】
{final_proposal}
================================================================
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ===== メイン =====
def main():
    log("=" * 50)
    log(f"メールパイプライン v4 起動（スキルフィルタリング追加）")
    log(f"設定: 取得{FETCH_LIMIT}件 / 処理{PROCESS_LIMIT}件 / マッチング上位{MATCH_TOP_N}名")

    processed = load_processed_ids()
    log(f"処理済みID: {len(processed)}件")

    emails = fetch_recent_emails(limit=FETCH_LIMIT)
    if not emails:
        log("処理対象なし・終了")
        return

    new_emails = [e for e in emails if e["msg_id"] not in processed]
    log(f"新規処理対象: {len(new_emails)}件（{len(emails) - len(new_emails)}件スキップ）")

    if not new_emails:
        log("全て処理済み・終了")
        return

    target_emails = new_emails[:PROCESS_LIMIT]
    if len(new_emails) > PROCESS_LIMIT:
        log(f"処理上限により{PROCESS_LIMIT}件に絞り込み（残り{len(new_emails)-PROCESS_LIMIT}件は次回）")

    engineers = get_available_engineers()
    log(f"エンジニアDB: {len(engineers)}名（稼働可能）")

    for em in target_emails:
        subject  = em["subject"]
        sender   = em["sender"]
        reply_to = em["reply_to"]
        body     = em["body"]
        msg_id   = em["msg_id"]
        log(f"処理中: {subject[:50]}")

        info = classify_email(subject, body)
        msg_type = info.get("type", "other")
        log(f"  判定: {msg_type}")

        if msg_type == "project":
            ok = register_project(info, subject, sender)
            proj_name = info.get("name") or subject[:30]
            if not ok:
                log(f"  [NG] 案件Notion登録失敗: {proj_name}")
                save_processed_id(msg_id, processed)
                continue
            log(f"  [OK] 案件登録: {proj_name}")

            # ★v4: Python側でスキルフィルタリング★
            filtered = filter_engineers_by_skills(info, engineers, top_n=MATCH_TOP_N)
            log(f"  スキルフィルタリング: {len(engineers)}名 → {len(filtered)}名")

            if not filtered:
                log(f"  [!!] スキルマッチする候補者なし: {proj_name}")
                save_processed_id(msg_id, processed)
                continue

            matching = ai_matching(info, filtered)
            candidates = matching.get("candidates", [])
            proposal_draft = matching.get("proposal_draft", "")

            if not candidates:
                log(f"  [!!] AIマッチング候補なし: {proj_name}")
                save_processed_id(msg_id, processed)
                continue
            log(f"  AIマッチング: {len(candidates)}名")

            check_input = f"【案件名】{proj_name}\n\n【提案文ドラフト】\n{proposal_draft}\n\n【候補者】\n"
            for c in candidates:
                check_input += f"- {c['name']} / {c.get('price',0)}万円 / 並行: {c.get('parallel','なし')}\n"
            check_result = double_check(check_input)

            final_proposal = proposal_draft
            marker = "【修正済み提案文】"
            if marker in check_result:
                after = check_result.split(marker, 1)[1].strip()
                if "【所見】" in after:
                    after = after.split("【所見】")[0].strip()
                if after and after != "修正不要":
                    final_proposal = after

            draft_path = save_draft(proj_name, reply_to, candidates, check_result, final_proposal)
            log(f"  [OK] 提案文下書き保存: {draft_path.name}")
            log(f"  [MAIL] 返信先: {reply_to}")

        elif msg_type == "engineer":
            name = info.get("name", "（名前未記載）")
            ok = register_engineer(info, subject, sender)
            if ok:
                log(f"  [OK] 人材登録: {name}")
            else:
                log(f"  [NG] 人材Notion登録失敗: {name}")

        else:
            log(f"  スキップ（その他）: {subject[:40]}")

        save_processed_id(msg_id, processed)

    log("メールパイプライン v4 完了")
    log("=" * 50)


if __name__ == "__main__":
    main()

```

