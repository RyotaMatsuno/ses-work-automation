import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
SES_WORK_DIR = BASE_DIR.parent
RESULT_JSON_PATH = SES_WORK_DIR / "matching_v2" / "result.json"
ENV_PATH = SES_WORK_DIR / "config" / ".env"
LINE_PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"
MAX_MESSAGE_LENGTH = 5000


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def load_results(result_path: Path) -> list[dict[str, Any]]:
    if not result_path.exists():
        log(f"ERROR: result.jsonが存在しません: {result_path}")
        raise FileNotFoundError(result_path)

    with result_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("result.jsonの形式が不正です: ルートは配列である必要があります")

    return data


def sort_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(candidate: dict[str, Any]) -> tuple[float, float]:
        score = candidate.get("score")
        price = candidate.get("price")
        score_value = float(score) if isinstance(score, (int, float)) else 0.0
        price_value = float(price) if isinstance(price, (int, float)) else float("inf")
        return (-score_value, price_value)

    return sorted(candidates, key=sort_key)


def format_candidate(index: int, candidate: dict[str, Any]) -> str:
    number = ["①", "②", "③"][index - 1] if 1 <= index <= 3 else f"{index}."
    name = str(candidate.get("engineer_name") or "(no name)")
    price = candidate.get("price")
    price_text = str(price) if price is not None else "-"
    needs_check = " [要確認]" if candidate.get("needs_check") is True else ""
    return f"  {number} {name}{needs_check} /{price_text}万"


def format_project(project: dict[str, Any]) -> str | None:
    candidates = project.get("candidates") or []
    if not isinstance(candidates, list) or len(candidates) == 0:
        return None

    project_name = str(project.get("project_name") or "(no project name)")
    project_url = str(project.get("project_url") or "")
    sorted_candidates = sort_candidates(candidates)

    lines = [
        f"■ {project_name}（{len(sorted_candidates)}名マッチ）",
        project_url,
    ]

    for index, candidate in enumerate(sorted_candidates[:3], start=1):
        lines.append(format_candidate(index, candidate))

    remaining_count = len(sorted_candidates) - 3
    if remaining_count > 0:
        lines.append(f"  他{remaining_count}名")

    return "\n".join(lines)


def split_messages(header: str, project_blocks: list[str]) -> list[str]:
    if not project_blocks:
        return [f"{header}\n\nマッチする案件はありません。"]

    messages: list[str] = []
    current = header

    for block in project_blocks:
        candidate_message = f"{current}\n\n{block}"
        if len(candidate_message) <= MAX_MESSAGE_LENGTH:
            current = candidate_message
            continue

        if current != header:
            messages.append(current)
            current = header
            candidate_message = f"{current}\n\n{block}"

        if len(candidate_message) <= MAX_MESSAGE_LENGTH:
            current = candidate_message
        else:
            messages.extend(split_long_block(header, block))
            current = header

    if current != header:
        messages.append(current)
    elif not messages:
        messages.append(header)

    return messages


def split_long_block(header: str, block: str) -> list[str]:
    messages: list[str] = []
    current = header

    for line in block.splitlines():
        candidate_message = f"{current}\n\n{line}" if current == header else f"{current}\n{line}"
        if len(candidate_message) <= MAX_MESSAGE_LENGTH:
            current = candidate_message
            continue

        if current != header:
            messages.append(current)
        current = f"{header}\n\n{line}"

    if current != header:
        messages.append(current)

    return messages


def build_messages(projects: list[dict[str, Any]]) -> list[str]:
    header = datetime.now().strftime("【マッチング結果】%Y-%m-%d %H:%M")
    project_blocks = []

    for project in projects:
        block = format_project(project)
        if block is not None:
            project_blocks.append(block)

    return split_messages(header, project_blocks)


def send_line_message(token: str, user_id: str, message: str, label: str) -> bool:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": message}],
    }

    try:
        response = requests.post(
            LINE_PUSH_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        log(f"ERROR: {label}へのLINE送信に失敗しました: {exc}")
        return False

    if response.status_code >= 400:
        log(f"ERROR: {label}へのLINE送信に失敗しました: status={response.status_code}, body={response.text}")
        return False

    log(f"INFO: {label}へLINE送信しました")
    return True


def get_recipients() -> list[dict[str, str]]:
    recipients = [
        {
            "label": "松野",
            "token_env": "LINE_CHANNEL_ACCESS_TOKEN",
            "user_id_env": "MATSUNO_LINE_USER_ID",
        },
        {
            "label": "岡本",
            "token_env": "OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN",
            "user_id_env": "OKAMOTO_LINE_USER_ID",
        },
    ]

    valid_recipients = []
    for recipient in recipients:
        token = os.getenv(recipient["token_env"])
        user_id = os.getenv(recipient["user_id_env"])
        if not token or not user_id:
            log(
                "WARN: "
                f"{recipient['label']}の環境変数が未設定のためskipします "
                f"({recipient['token_env']}, {recipient['user_id_env']})"
            )
            continue

        valid_recipients.append({
            "label": recipient["label"],
            "token": token,
            "user_id": user_id,
        })

    return valid_recipients


def run(dry_run: bool) -> int:
    load_dotenv(dotenv_path=ENV_PATH, encoding="utf-8")
    log(f"INFO: .env読み込み: {ENV_PATH}")

    try:
        projects = load_results(RESULT_JSON_PATH)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        log(f"ERROR: result.json読み込みに失敗しました: {exc}")
        return 1

    messages = build_messages(projects)
    log(f"INFO: 通知メッセージを作成しました: {len(messages)}通")

    if dry_run:
        for index, message in enumerate(messages, start=1):
            log(f"DRY-RUN: message {index}/{len(messages)} length={len(message)}")
            print(message)
            print("-" * 40)
        return 0

    recipients = get_recipients()
    if not recipients:
        log("WARN: 送信可能な宛先がありません")
        return 0

    for recipient in recipients:
        for message in messages:
            send_line_message(recipient["token"], recipient["user_id"], message, recipient["label"])

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="matching_v2/result.jsonの内容をLINEへ通知します")
    parser.add_argument("--dry-run", action="store_true", help="LINE送信せずコンソールに出力します")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
