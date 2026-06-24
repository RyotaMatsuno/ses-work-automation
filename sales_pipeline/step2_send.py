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
        entry = {
            "step": "intent",
            "path": str(path),
            "to": to,
            "subject": subject,
            "dry_run": dry_run,
            "at": datetime.now().isoformat(),
        }
        if dry_run:
            entry["status"] = "skipped"
            print("[Step2] dry-run: メール送信スキップ", flush=True)
        else:
            payload = json.dumps(
                {"account": "sessales", "to": to, "subject": subject, "body": body}, ensure_ascii=False
            ).encode("utf-8")
            try:
                req = urllib.request.Request(
                    endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST"
                )
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
