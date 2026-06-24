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
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(file)]


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
