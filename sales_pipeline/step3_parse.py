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
            req = urllib.request.Request(
                f"http://{host}:{port}{path}", data=payload, headers={"Content-Type": "application/json"}, method="POST"
            )
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
