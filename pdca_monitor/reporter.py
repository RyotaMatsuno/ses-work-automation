"""Weekly PDCA report: aggregate logs, Claude summary, LINE + Notion."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
SES_WORK = BASE_DIR.parent
ENV_PATH = SES_WORK / "config" / ".env"
LOG_DIR = BASE_DIR / "logs"

sys.path.insert(0, str(SES_WORK))
from db import get_weekly_summary, week_range_for_report  # noqa: E402

from common.ledger import can_spend, record  # noqa: E402
from common.model_config import VISION_MODEL  # noqa: E402

NOTION_API_VERSION = "2022-06-28"
WIKI_PAGE_ID = "353450ff-37c0-8145-9e3e-d80c8c8ed594"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
REPORT_MODEL = VISION_MODEL  # claude-sonnet-4-6
SCRIPT_NAME = "pdca_monitor"
JST = timezone(timedelta(hours=9))

MAIL_LOG_CANDIDATES = [
    SES_WORK / "logs" / "mail_pipeline.log",
    SES_WORK / "mail_pipeline" / "pipeline.log",
]
MATCH_LOG_CANDIDATES = [
    SES_WORK / "logs" / "matching_v3.log",
    SES_WORK / "logs" / "matching_daily.log",
    SES_WORK / "matching_v3" / "logs" / "match_results.jsonl",
]


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"reporter_{datetime.now(JST).strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_env() -> dict[str, str]:
    env = dotenv_values(ENV_PATH, encoding="utf-8") if ENV_PATH.exists() else {}
    return {k: (v or "").strip().strip("'\"") for k, v in env.items()}


def _parse_line_timestamp(line: str) -> datetime | None:
    patterns = [
        r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]",
        r"\[(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\]",
    ]
    for pattern in patterns:
        match = re.search(pattern, line)
        if not match:
            continue
        raw = match.group(1).replace("/", "-")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=JST)
            except ValueError:
                continue
    return None


def _in_range(ts: datetime, start: datetime, end: datetime) -> bool:
    return start <= ts <= end


def count_mail_pipeline_runs(start: str, end: str) -> int:
    start_dt = datetime.fromisoformat(f"{start}T00:00:00").replace(tzinfo=JST)
    end_dt = datetime.fromisoformat(f"{end}T23:59:59").replace(tzinfo=JST)
    log_path = next((p for p in MAIL_LOG_CANDIDATES if p.exists()), None)
    if not log_path:
        logging.warning("mail pipeline log not found")
        return 0

    count = 0
    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "mail_pipeline 開始" not in line and "全処理完了" not in line:
                continue
            ts = _parse_line_timestamp(line)
            if ts and _in_range(ts, start_dt, end_dt):
                count += 1
    return count // 2 if count else 0


def count_matching_runs(start: str, end: str) -> int:
    start_dt = datetime.fromisoformat(f"{start}T00:00:00").replace(tzinfo=JST)
    end_dt = datetime.fromisoformat(f"{end}T23:59:59").replace(tzinfo=JST)

    jsonl = SES_WORK / "matching_v3" / "logs" / "match_results.jsonl"
    if jsonl.exists():
        cases: set[str] = set()
        with jsonl.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts_raw = row.get("ts", "")
                try:
                    ts = datetime.fromisoformat(ts_raw)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=JST)
                    else:
                        ts = ts.astimezone(JST)
                except ValueError:
                    continue
                if _in_range(ts, start_dt, end_dt):
                    cases.add(f"{row.get('case_id')}:{ts.date().isoformat()}")
        if cases:
            return len(cases)

    log_path = next((p for p in MATCH_LOG_CANDIDATES if p.exists() and p.suffix == ".log"), None)
    if not log_path:
        logging.warning("matching log not found")
        return 0

    count = 0
    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "マッチング開始" not in line and "matching_v3" not in line.lower():
                continue
            ts = _parse_line_timestamp(line)
            if ts and _in_range(ts, start_dt, end_dt) and "開始" in line:
                count += 1
    return count


def notion_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }


def fetch_ai_queue_counts(api_key: str, queue_db_id: str, start: str, end: str) -> dict[str, int]:
    url = f"https://api.notion.com/v1/databases/{queue_db_id}/query"
    counts = {"done": 0, "blocked": 0}
    payload: dict[str, Any] = {"page_size": 100}
    filter_body = {
        "and": [
            {
                "or": [
                    {"property": "状態", "select": {"equals": "done"}},
                    {"property": "状態", "select": {"equals": "blocked"}},
                ]
            },
            {"property": "完了日時", "date": {"on_or_after": start}},
            {"property": "完了日時", "date": {"on_or_before": end}},
        ]
    }
    payload["filter"] = filter_body

    while True:
        resp = requests.post(url, headers=notion_headers(api_key), json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for page in data.get("results", []):
            props = page.get("properties", {})
            status_prop = props.get("状態", {})
            status = ""
            if status_prop.get("type") == "select" and status_prop.get("select"):
                status = status_prop["select"].get("name", "")
            if status in counts:
                counts[status] += 1
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    return counts


def build_metrics(start: str, end: str, env: dict[str, str], mock: bool) -> dict[str, Any]:
    summary = get_weekly_summary(start, end)
    if mock:
        ai_counts = {"done": 3, "blocked": 1}
        mail_count = 42
        match_count = 5
    else:
        api_key = env.get("NOTION_API_KEY", "")
        queue_db = env.get("NOTION_AI_QUEUE_DB_ID", "")
        ai_counts = {"done": 0, "blocked": 0}
        if api_key and queue_db:
            try:
                ai_counts = fetch_ai_queue_counts(api_key, queue_db, start, end)
            except Exception as exc:
                logging.error("AI queue fetch failed: %s", exc)
        mail_count = count_mail_pipeline_runs(start, end)
        match_count = count_matching_runs(start, end)

    return {
        "summary": summary,
        "ai_done": ai_counts.get("done", 0),
        "ai_blocked": ai_counts.get("blocked", 0),
        "mail_count": mail_count,
        "match_count": match_count,
    }


def generate_ai_content(metrics: dict[str, Any], mock: bool) -> dict[str, Any]:
    summary = metrics["summary"]
    prompt = f"""あなたはSES事業の経営参謀です。以下の週次データからPDCAレポート用のJSONを生成してください。

データ:
{json.dumps(metrics, ensure_ascii=False, indent=2)}

出力は必ずJSONのみ（説明文不要）:
{{
  "automation_suggestions": ["具体的な自動化提案1", "提案2", "提案3"],
  "automation_details": "自動化提案の詳細（SPEC候補として200-400字）",
  "cursor_tasks": ["来週のCursorタスク候補1", "候補2", "候補3"]
}}
"""
    if mock:
        return {
            "automation_suggestions": [
                "メール分類後のNotion登録エラーを自動リトライ",
                "マッチング結果の週次サマリーをSlack代替でLINE配信",
                "PC操作ログから繰り返し作業を検出してマクロ化",
            ],
            "automation_details": "週次で同一アプリに30%以上の時間を使っている場合、ショートカットまたは自動化スクリプト化を優先検討する。",
            "cursor_tasks": [
                "mail_pipeline エラー自動リトライ",
                "matching_v3 staleness bug 修正",
                "pdca_monitor OCR精度チューニング",
            ],
        }

    if not can_spend(est_in=2500, est_out=800, model=REPORT_MODEL):
        raise RuntimeError("CostGuard: API呼び出しを拒否しました")

    api_key = load_env().get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=REPORT_MODEL,
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text if message.content else "{}"
    record(
        message.usage.input_tokens,
        message.usage.output_tokens,
        REPORT_MODEL,
        SCRIPT_NAME,
    )

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise RuntimeError("Claude response did not contain JSON")
    return json.loads(match.group(0))


def format_line_message(
    week_label: str,
    metrics: dict[str, Any],
    ai_content: dict[str, Any],
    notion_url: str,
) -> str:
    summary = metrics["summary"]
    top3 = summary.get("app_usage", [])[:3]
    suggestions = ai_content.get("automation_suggestions", [])[:3]

    lines = [
        f"📊 週次PDCAレポート（{week_label}）",
        "",
        "【今週の実績】",
        f"・AI作業: 完了{metrics['ai_done']}件 / blocked{metrics['ai_blocked']}件",
        f"・メール処理: {metrics['mail_count']}件",
        f"・マッチング: {metrics['match_count']}件",
        "",
        "【PC使用時間TOP3】",
    ]
    for idx, item in enumerate(top3, start=1):
        lines.append(f"{idx}. {item['app_name']}: {item['minutes']}分")
    if not top3:
        lines.append("（データなし）")

    lines.extend(["", "【自動化提案】"])
    for suggestion in suggestions:
        lines.append(f"・{suggestion}")
    if not suggestions:
        lines.append("・（提案なし）")

    lines.extend(["", "詳細はNotionで確認:", notion_url])
    return "\n".join(lines)


def _block_paragraph(text: str) -> dict[str, Any]:
    chunks = [text[i : i + 1800] for i in range(0, len(text), 1800)] or [""]
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}] for chunk in chunks},
    }


def _block_heading(text: str, level: int = 2) -> dict[str, Any]:
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]},
    }


def _block_bullet(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]},
    }


def create_notion_page(
    api_key: str,
    title: str,
    line_message: str,
    metrics: dict[str, Any],
    ai_content: dict[str, Any],
) -> str:
    summary = metrics["summary"]
    children: list[dict[str, Any]] = [
        _block_heading("LINEメッセージ全文"),
        _block_paragraph(line_message),
        _block_heading("アプリ使用時間"),
    ]
    for item in summary.get("app_usage", []):
        children.append(_block_bullet(f"{item['app_name']}: {item['minutes']}分"))

    children.append(_block_heading("キーワード TOP20"))
    for item in summary.get("top_keywords", []):
        children.append(_block_bullet(f"{item['keyword']}: {item['count']}"))

    children.append(_block_heading("自動化提案（詳細）"))
    children.append(_block_paragraph(ai_content.get("automation_details", "")))

    children.append(_block_heading("来週のCursorタスク候補"))
    for task in ai_content.get("cursor_tasks", []):
        children.append(_block_bullet(task))

    body = {
        "parent": {"page_id": WIKI_PAGE_ID},
        "properties": {"title": {"title": [{"type": "text", "text": {"content": title[:200]}}]}},
        "children": children[:100],
    }
    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=notion_headers(api_key),
        json=body,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("url", "")


def send_line_message(token: str, user_id: str, text: str) -> None:
    resp = requests.post(
        LINE_PUSH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"to": user_id, "messages": [{"type": "text", "text": text[:5000]}]},
        timeout=30,
    )
    resp.raise_for_status()


def run_report(mock: bool = False) -> dict[str, Any]:
    setup_logging()
    env = load_env()
    start, end = week_range_for_report()
    week_label = datetime.fromisoformat(start).strftime("%m/%d") + "週"

    logging.info("report range: %s - %s (mock=%s)", start, end, mock)
    metrics = build_metrics(start, end, env, mock=mock)
    ai_content = generate_ai_content(metrics, mock=mock)

    notion_url = "https://www.notion.so/mock-pdca-report"
    if mock:
        line_message = format_line_message(week_label, metrics, ai_content, notion_url)
        logging.info("MOCK LINE message:\n%s", line_message)
        return {
            "week_label": week_label,
            "line_message": line_message,
            "notion_url": notion_url,
            "metrics": metrics,
            "ai_content": ai_content,
        }

    api_key = env.get("NOTION_API_KEY", "")
    line_token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = env.get("MATSUNO_LINE_USER_ID", "Ue3508b43b84991f5a68281da5bf4cf39")

    title = f"週次PDCAレポート {start}〜{end}"
    line_message = format_line_message(
        week_label,
        metrics,
        ai_content,
        "https://www.notion.so/",
    )
    notion_url = create_notion_page(api_key, title, line_message, metrics, ai_content)
    line_message = format_line_message(week_label, metrics, ai_content, notion_url)

    send_line_message(line_token, user_id, line_message)
    logging.info("report sent. notion=%s", notion_url)
    return {"notion_url": notion_url, "line_message": line_message}


def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly PDCA reporter")
    parser.add_argument("--mock", action="store_true", help="Skip external API calls")
    args = parser.parse_args()
    try:
        run_report(mock=args.mock)
    except Exception as exc:
        logging.exception("reporter failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
