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
