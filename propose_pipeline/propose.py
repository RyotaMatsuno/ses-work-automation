# -*- coding: utf-8 -*-
from __future__ import annotations

import imaplib
import json
import os
import re
import ssl
import sys
import time
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Any


sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parents[1]
RESULT_JSON = BASE_DIR / "matching_v2" / "result.json"
ENV_PATH = BASE_DIR / "config" / ".env"

IMAP_HOST = "mail65.onamae.ne.jp"
IMAP_PORT = 993
MIN_GROSS_YEN = 50000
MAX_PROPOSALS = 3
DEFAULT_TO = "proposal@example.com"

ACCOUNT_KEYS = {
    "松野": ("MATSUNO_EMAIL", "MATSUNO_PASSWORD", "r-matsuno@terra-ltd.co.jp"),
    "岡本": ("OKAMOTO_EMAIL", "OKAMOTO_PASSWORD", "r-okamoto@terra-ltd.co.jp"),
    "": ("SESSALES_EMAIL", "SESSALES_PASSWORD", "sessales@terra-ltd.co.jp"),
}


@dataclass
class ProposalCandidate:
    data: dict[str, Any]
    price_yen: int
    gross_yen: int
    summary: str


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        env[key.strip()] = value
    return env


def load_projects(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"result.jsonが存在しません: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    raise ValueError("result.jsonの形式が配列ではありません")


def normalize_price(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        price = int(float(str(value).replace(",", "").strip()))
    except ValueError:
        return None
    if price <= 100:
        return price * 10000
    return price


def yen_to_man(value: int | None) -> int:
    if value is None:
        return 0
    return value // 10000


def is_all_required_ok(candidate: dict[str, Any]) -> bool:
    required = candidate.get("required") or {}
    if not required:
        return False
    for result in required.values():
        if not isinstance(result, dict):
            return False
        if result.get("result") != "◯":
            return False
    return True


def optional_ok_ratio(candidate: dict[str, Any]) -> tuple[int, int]:
    optional = candidate.get("optional") or {}
    total = len(optional)
    ok = 0
    for result in optional.values():
        if isinstance(result, dict) and result.get("result") == "◯":
            ok += 1
    return ok, total


def build_summary(candidate: dict[str, Any]) -> str:
    ok, total = optional_ok_ratio(candidate)
    if total > 0 and ok == total:
        return "必須・尚可ともにマッチ度高い人員"
    if total > 0 and ok / total >= 0.5:
        return "必須全て満たしており、尚可も経験あり"
    return "必須スキル全て満たし即稼働可能"


def select_candidates(project: dict[str, Any]) -> tuple[list[ProposalCandidate], str | None]:
    candidates = project.get("candidates") or []
    if not candidates:
        return [], "候補なし"

    budget_yen = normalize_price(project.get("budget"))
    if budget_yen is None:
        return [], "予算なし"

    required_ok_count = 0
    proposals: list[ProposalCandidate] = []
    for candidate in candidates:
        if not is_all_required_ok(candidate):
            continue
        required_ok_count += 1

        price_yen = normalize_price(candidate.get("price"))
        if price_yen is None:
            continue

        gross_yen = budget_yen - price_yen
        if gross_yen < MIN_GROSS_YEN:
            continue

        proposals.append(
            ProposalCandidate(
                data=candidate,
                price_yen=price_yen,
                gross_yen=gross_yen,
                summary=build_summary(candidate),
            )
        )

    if not proposals:
        if required_ok_count == 0:
            return [], "全員必須×"
        return [], "粗利不足"

    proposals.sort(key=lambda item: item.gross_yen, reverse=True)
    return proposals[:MAX_PROPOSALS], None


def resolve_owner(project: dict[str, Any]) -> str:
    owner = str(project.get("project_owner") or "").strip()
    if owner:
        return owner
    for candidate in project.get("candidates") or []:
        owner = str(candidate.get("project_owner") or "").strip()
        if owner:
            return owner
    return ""


def resolve_from(project: dict[str, Any], env: dict[str, str]) -> tuple[str, str | None, str | None]:
    owner = resolve_owner(project)
    email_key, pass_key, default_email = ACCOUNT_KEYS.get(owner, ACCOUNT_KEYS[""])
    from_email = env.get(email_key) or default_email
    password = env.get(pass_key)
    return from_email, password, owner


def extract_to_address(project: dict[str, Any]) -> str:
    raw_body = str(project.get("raw_body") or "")
    sender_match = re.search(r"送信者:\s*.*?<([^<>\s]+@[^<>\s]+)>", raw_body)
    if sender_match:
        return sender_match.group(1)
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", raw_body)
    if email_match:
        return email_match.group(0)
    return DEFAULT_TO


def build_skill_line(skills: dict[str, Any]) -> str:
    if not skills:
        return "なし"
    parts = []
    for skill, result in skills.items():
        mark = result.get("result", "未設定") if isinstance(result, dict) else "未設定"
        parts.append(f"{skill}: {mark}")
    return ", ".join(parts)


def build_body(project: dict[str, Any], proposals: list[ProposalCandidate]) -> str:
    summaries = []
    marks = "①②③"
    for index, proposal in enumerate(proposals):
        summaries.append(f"{marks[index]}に関しては{proposal.summary}")
    summary_text = "、".join(summaries) + "でございます。"

    lines = [
        "ご担当者様",
        "",
        "いつもお世話になっております。",
        "",
        "案件ご紹介いただきありがとうございます。",
        f"下記{len(proposals)}名いかがでしょうか。",
        summary_text,
        "",
        "ご検討いただけますと幸いです。",
        "",
    ]

    for index, proposal in enumerate(proposals):
        candidate = proposal.data
        lines.extend(
            [
                "━━━━━━━━━━━━━━━━━━",
                f"{marks[index]} {candidate.get('engineer_name', '氏名未設定')}様",
                f" 単価: {yen_to_man(proposal.price_yen)}万円",
                f" 稼働開始: {candidate.get('available_date') or '即日'}",
                " 並行: なし（確認要）",
                " [スキル詳細]",
                f" 必須: {build_skill_line(candidate.get('required') or {})}",
            ]
        )
    lines.extend(
        [
            "━━━━━━━━━━━━━━━━━━",
            "",
            "何卒よろしくお願いいたします。",
        ]
    )
    return "\n".join(lines)


def build_message(subject: str, body: str, from_email: str, to_email: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.set_content(body, subtype="plain", charset="utf-8")
    return msg


def append_draft(from_email: str, password: str, msg: EmailMessage) -> None:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=context) as mail:
        mail.login(from_email, password)
        internal_date = imaplib.Time2Internaldate(time.time())
        status, _ = mail.append("Drafts", "\\Draft", internal_date, msg.as_bytes())
        if status != "OK":
            raise RuntimeError(f"IMAP APPEND failed: {status}")


def print_project_result(
    project_name: str,
    proposals: list[ProposalCandidate],
    from_email: str,
    subject: str,
    status_label: str,
) -> None:
    print(f"[{project_name}] → 提案人数{len(proposals)}名 → {status_label}: {from_email} ({subject})")
    marks = "①②③"
    for index, proposal in enumerate(proposals):
        name = proposal.data.get("engineer_name", "氏名未設定")
        print(
            f"  {marks[index]}{name} "
            f"単価{yen_to_man(proposal.price_yen)}万 "
            f"粗利{yen_to_man(proposal.gross_yen)}万"
        )


def main() -> int:
    dry_run = os.environ.get("DRY_RUN") == "1"
    env = load_env(ENV_PATH)

    try:
        projects = load_projects(RESULT_JSON)
    except Exception as exc:
        print(f"エラー: {exc}")
        return 1

    if dry_run:
        print("[DRY_RUN] IMAP接続せず、コンソール出力のみ実行します")

    for project in projects:
        project_name = project.get("project_name") or "案件名未設定"
        proposals, skip_reason = select_candidates(project)
        if skip_reason:
            print(f"スキップ: [{project_name}] → {skip_reason}")
            continue

        from_email, password, _owner = resolve_from(project, env)
        to_email = extract_to_address(project)
        subject = f"【ご提案】{project_name}"
        body = build_body(project, proposals)
        msg = build_message(subject, body, from_email, to_email)

        if dry_run:
            print_project_result(project_name, proposals, from_email, subject, "DRY_RUN")
            print(body)
            print("")
            continue

        if not password:
            print(f"エラー: [{project_name}] → IMAPパスワード未設定のためスキップ: {from_email}")
            continue

        try:
            append_draft(from_email, password, msg)
        except Exception as exc:
            print(f"エラー: [{project_name}] → 下書き保存失敗: {exc}")
            continue

        print_project_result(project_name, proposals, from_email, subject, "下書き保存")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
