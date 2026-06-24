# -*- coding: utf-8 -*-
"""LINE bridge worker health check: trigger worker, inspect Notion queue, alert on failure."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
SES_WORK_DIR = BASE_DIR.parent
ENV_PATH = SES_WORK_DIR / "config" / ".env"
LOG_PATH = BASE_DIR / "worker_health.log"

JST = timezone(timedelta(hours=9))
NOTION_VERSION = "2022-06-28"
DEFAULT_CLOUD_RUN_URL = "https://line-webhook-74735301292.asia-northeast1.run.app"
DEFAULT_CRON_TOKEN = "jobz-bridge-2026"
RUNNING_STALE_MINUTES = 30
LINE_PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"


@dataclass
class WorkerCheckResult:
    ok: bool
    status_code: int
    body: str = ""
    error: str = ""


@dataclass
class QueueStats:
    queued_count: int = 0
    running_count: int = 0
    stale_running: list[dict[str, str]] = field(default_factory=list)
    error: str = ""


@dataclass
class HealthReport:
    worker: WorkerCheckResult
    queue: QueueStats
    alerts: list[str] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return not self.alerts


def log(message: str) -> None:
    timestamp = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as file:
            file.write(line + "\n")
    except OSError:
        pass


def _strip_env(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().strip("'\"")


def load_env() -> None:
    load_dotenv(dotenv_path=ENV_PATH, encoding="utf-8")
    log(f"INFO: .env loaded from {ENV_PATH}")


def cloud_run_url() -> str:
    return os.getenv("CLOUD_RUN_URL", DEFAULT_CLOUD_RUN_URL).rstrip("/")


def cron_token() -> str:
    return _strip_env(os.getenv("LINE_BRIDGE_CRON_TOKEN", DEFAULT_CRON_TOKEN))


def queue_db_id() -> str:
    return _strip_env(os.getenv("NOTION_AI_QUEUE_DB_ID", ""))


def notion_headers() -> dict[str, str]:
    api_key = os.getenv("NOTION_API_KEY", "")
    db_id = queue_db_id()
    if not api_key:
        raise RuntimeError("NOTION_API_KEY is not configured")
    if not db_id:
        raise RuntimeError("NOTION_AI_QUEUE_DB_ID is not configured")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def trigger_worker(timeout: int = 120) -> WorkerCheckResult:
    url = f"{cloud_run_url()}/line-bridge/worker"
    headers = {"X-Line-Bridge-Token": cron_token()}
    try:
        response = requests.post(url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        return WorkerCheckResult(
            ok=False,
            status_code=0,
            error=f"worker request failed: {exc}",
        )
    body = response.text[:500]
    ok = response.status_code < 500
    return WorkerCheckResult(
        ok=ok,
        status_code=response.status_code,
        body=body,
        error="" if ok else f"worker returned HTTP {response.status_code}",
    )


def _extract_text(prop: dict[str, Any]) -> str:
    values = prop.get("title") or prop.get("rich_text") or []
    return "".join(item.get("plain_text", "") for item in values)


def _query_status_pages(status: str) -> tuple[list[dict[str, Any]], str | None]:
    db_id = queue_db_id()
    pages: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        payload: dict[str, Any] = {
            "filter": {
                "property": "状態",
                "select": {"equals": status},
            },
            "page_size": 100,
        }
        if cursor:
            payload["start_cursor"] = cursor
        try:
            response = requests.post(
                f"https://api.notion.com/v1/databases/{db_id}/query",
                headers=notion_headers(),
                json=payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            return [], f"Notion query failed ({status}): {exc}"
        if response.status_code >= 400:
            return [], (f"Notion query failed ({status}): HTTP {response.status_code} {response.text[:200]}")
        data = response.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return pages, None


def _parse_notion_time(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(JST)


def inspect_queue(stale_minutes: int = RUNNING_STALE_MINUTES) -> QueueStats:
    queued_pages, queued_error = _query_status_pages("queued")
    running_pages, running_error = _query_status_pages("running")
    error = queued_error or running_error or ""
    if error:
        return QueueStats(error=error)

    cutoff = datetime.now(JST) - timedelta(minutes=stale_minutes)
    stale_running: list[dict[str, str]] = []
    for page in running_pages:
        props = page.get("properties", {})
        task_id = _extract_text(props.get("task_id", {}))
        edited_at = _parse_notion_time(page.get("last_edited_time", ""))
        if edited_at and edited_at <= cutoff:
            stale_running.append(
                {
                    "task_id": task_id or page.get("id", ""),
                    "last_edited": edited_at.strftime("%Y-%m-%d %H:%M"),
                }
            )

    return QueueStats(
        queued_count=len(queued_pages),
        running_count=len(running_pages),
        stale_running=stale_running,
    )


def build_report(
    worker: WorkerCheckResult,
    queue: QueueStats,
) -> HealthReport:
    alerts: list[str] = []

    if not worker.ok:
        detail = worker.error or f"HTTP {worker.status_code}"
        alerts.append(f"worker異常: {detail}")

    if queue.error:
        alerts.append(f"Notion確認失敗: {queue.error}")

    if queue.stale_running:
        task_ids = ", ".join(item["task_id"] for item in queue.stale_running[:5])
        alerts.append(f"running停滞({RUNNING_STALE_MINUTES}分超): {len(queue.stale_running)}件 [{task_ids}]")

    return HealthReport(worker=worker, queue=queue, alerts=alerts)


def build_status_message(report: HealthReport) -> str:
    worker = report.worker
    queue = report.queue
    lines = [
        "【LINE bridge worker ヘルスチェック】",
        datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        f"worker: HTTP {worker.status_code}",
        f"queued: {queue.queued_count} / running: {queue.running_count}",
    ]
    if report.alerts:
        lines.append("異常:")
        lines.extend(f"- {alert}" for alert in report.alerts)
    else:
        lines.append("状態: 正常")
    return "\n".join(lines)


def build_alert_message(report: HealthReport) -> str:
    lines = [
        "【LINE bridge worker 異常検知】",
        datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        f"queued: {report.queue.queued_count} / running: {report.queue.running_count}",
    ]
    lines.extend(f"- {alert}" for alert in report.alerts)
    if report.worker.body and not report.worker.ok:
        lines.append(f"worker body: {report.worker.body[:200]}")
    return "\n".join(lines)


def send_line_alert(message: str) -> bool:
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = os.getenv("MATSUNO_LINE_USER_ID", "")
    if not token or not user_id:
        log("WARN: LINE通知スキップ（LINE_CHANNEL_ACCESS_TOKEN / MATSUNO_LINE_USER_ID 未設定）")
        return False
    try:
        response = requests.post(
            LINE_PUSH_ENDPOINT,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "to": user_id,
                "messages": [{"type": "text", "text": message[:5000]}],
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        log(f"ERROR: LINE通知失敗: {exc}")
        return False
    if response.status_code >= 400:
        log(f"ERROR: LINE通知失敗: status={response.status_code} body={response.text[:200]}")
        return False
    log("INFO: LINE異常通知を送信しました")
    return True


def run(
    *,
    dry_run: bool = False,
    skip_worker: bool = False,
) -> int:
    load_env()

    worker = WorkerCheckResult(ok=True, status_code=0, body="skipped")
    if skip_worker:
        log("INFO: worker trigger skipped")
    else:
        log(f"INFO: triggering worker at {cloud_run_url()}/line-bridge/worker")
        worker = trigger_worker()
        log(f"INFO: worker response status={worker.status_code} body={worker.body[:200]}")

    try:
        queue = inspect_queue()
    except RuntimeError as exc:
        queue = QueueStats(error=str(exc))

    report = build_report(
        worker,
        queue,
    )
    status_message = build_status_message(report)
    log(status_message.replace("\n", " | "))

    if dry_run:
        print(status_message)
        if report.alerts:
            print("-" * 40)
            print(build_alert_message(report))
        return 0 if report.healthy else 1

    if report.alerts:
        send_line_alert(build_alert_message(report))
        return 1

    log("INFO: health check passed")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LINE bridge worker health check and Notion queue monitor")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="LINE通知せず結果を標準出力に表示",
    )
    parser.add_argument(
        "--skip-worker",
        action="store_true",
        help="workerトリガーを省略（Notion確認のみ）",
    )
    parser.add_argument(
        action="store_true",
        help="worker 5xx異常をシミュレート（テスト用）",
    )
    parser.add_argument(
        action="store_true",
        help="running停滞異常をシミュレート（テスト用）",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run(
        dry_run=args.dry_run,
        skip_worker=args.skip_worker,
    )


if __name__ == "__main__":
    raise SystemExit(main())
