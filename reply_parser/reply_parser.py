from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent
WORK_DIR = BASE_DIR.parent
ENV_PATH = WORK_DIR / "config" / ".env"
LOG_PATH = BASE_DIR / "logs" / "reply_parser.log"
SAMPLE_PATH = BASE_DIR / "test_data" / "sample_reply.txt"

NOTION_API_VERSION = "2022-06-28"
ANTHROPIC_VERSION = "2023-06-01"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

SCORE_RULES = {
    "面談調整中": 1.5,
    "面談予定": 2.0,
    "オファー中": 5.0,
    "並行なし": 0.0,
    "なし": 0.0,
}


def log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(message + "\n")
    print(message, flush=True)


def load_config() -> dict[str, str]:
    cfg = dotenv_values(str(ENV_PATH))
    return {k: v for k, v in cfg.items() if v}


def notion_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }


def query_engineer_page(
    cfg: dict[str, str],
    engineer_name: str | None = None,
    page_id: str | None = None,
) -> dict[str, Any] | None:
    if page_id:
        res = requests.get(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=notion_headers(required(cfg, "NOTION_API_KEY")),
            timeout=20,
        )
        res.raise_for_status()
        return res.json()

    if not engineer_name:
        return None

    db_id = required(cfg, "NOTION_ENGINEER_DB_ID")
    payload = {
        "page_size": 1,
        "filter": {"property": "名前", "title": {"contains": engineer_name}},
    }
    res = requests.post(
        f"https://api.notion.com/v1/databases/{db_id}/query",
        headers=notion_headers(required(cfg, "NOTION_API_KEY")),
        json=payload,
        timeout=20,
    )
    res.raise_for_status()
    rows = res.json().get("results", [])
    return rows[0] if rows else None


def required(cfg: dict[str, str], key: str) -> str:
    value = cfg.get(key)
    if not value:
        raise RuntimeError(f"{key} is not set in {ENV_PATH}")
    return value


def build_prompt(body: str) -> str:
    return f"""返信メール本文から並行状況とスキル判定を抽出してください。

出力はJSONのみ。説明文やMarkdownは禁止。
schema:
{{
  "parallel_items": [
    {{"status": "面談調整中|面談予定|結果待ち|オファー中|並行なし|なし|その他", "days_waiting": 数値またはnull, "evidence": "根拠文"}}
  ],
  "required_skills": {{"スキル名": "○または×"}},
  "preferred_skills": {{"スキル名": "○または×"}},
  "notes": "補足"
}}

結果待ちは本文に日数があればdays_waitingへ数値で入れてください。
○/◯/可/OKは○、×/不可/NGは×に正規化してください。

本文:
{body}
"""


def call_claude(body: str, api_key: str) -> dict[str, Any]:
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1200,
        "temperature": 0,
        "messages": [{"role": "user", "content": build_prompt(body)}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=60,
    )
    res.raise_for_status()
    data = res.json()
    text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text").strip()
    return json.loads(extract_json(text))


def extract_json(text: str) -> str:
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError("Claude response does not contain JSON")
    return match.group(0)


def regex_extract(body: str) -> dict[str, Any]:
    items = []
    for line in body.splitlines():
        clean = line.strip()
        if not clean:
            continue
        for status in ("面談調整中", "面談予定", "結果待ち", "オファー中", "並行なし"):
            if status in clean:
                days = None
                m = re.search(r"(\d+)\s*日", clean)
                if m:
                    days = int(m.group(1))
                items.append({"status": status, "days_waiting": days, "evidence": clean})
                break
        if re.search(r"並行\s*[:：]?\s*なし", clean):
            items.append({"status": "並行なし", "days_waiting": None, "evidence": clean})

    return {
        "parallel_items": items or [{"status": "なし", "days_waiting": None, "evidence": ""}],
        "required_skills": parse_skill_block(body, "必須"),
        "preferred_skills": parse_skill_block(body, "尚可"),
        "notes": "regex fallback",
    }


def parse_skill_block(body: str, title: str) -> dict[str, str]:
    found: dict[str, str] = {}
    capture = False
    for line in body.splitlines():
        clean = line.strip()
        if title in clean:
            capture = True
            continue
        if capture and re.search(r"(必須|尚可|並行|提案|以上)", clean) and title not in clean:
            if not re.search(r"[:：]\s*[○◯×xX]|[○◯×xX]\s*$", clean):
                break
        if not capture:
            continue
        m = re.search(r"^[・\-*]?\s*([^:：○◯×xX]+?)\s*[:：]\s*([○◯×xX]|OK|NG|可|不可)\s*$", clean)
        if not m:
            m = re.search(r"^[・\-*]?\s*([^:：○◯×xX]+?)\s+([○◯×xX])\s*$", clean)
        if m:
            found[m.group(1).strip()] = normalize_mark(m.group(2))
    return found


def normalize_mark(value: str) -> str:
    return "×" if value.lower() in {"×", "x", "ng", "不可"} else "○"


def score_result_waiting(days_waiting: int | None) -> float:
    if days_waiting is None:
        return 1.5
    if days_waiting <= 2:
        return 1.0
    if days_waiting <= 5:
        return 1.5
    return 2.5


def calculate_parallel_score(items: list[dict[str, Any]]) -> float:
    total = 0.0
    for item in items:
        status = str(item.get("status") or "")
        if status == "結果待ち":
            total += score_result_waiting(item.get("days_waiting"))
        else:
            total += SCORE_RULES.get(status, 0.0)
    return round(total, 1)


def judge_proposal(score: float, required_skills: dict[str, str]) -> tuple[str, str]:
    missing = [name for name, mark in required_skills.items() if mark != "○"]
    if not required_skills:
        return "要確認", "必須スキル判定が抽出できません"
    if score >= 5.0:
        return "NG", f"並行スコアが5.0以上です（{score}）"
    if missing:
        return "NG", "必須スキルに×があります: " + ", ".join(missing)
    return "OK", "並行スコア5.0未満かつ必須スキル全○"


def analyze_reply(body: str, cfg: dict[str, str], use_claude: bool = True) -> dict[str, Any]:
    if use_claude and cfg.get("ANTHROPIC_API_KEY"):
        try:
            parsed = call_claude(body, cfg["ANTHROPIC_API_KEY"])
            parsed["notes"] = parsed.get("notes") or "claude"
        except Exception as exc:
            log(f"[reply_parser] Claude解析失敗、regexにフォールバック: {exc}")
            parsed = regex_extract(body)
    else:
        parsed = regex_extract(body)

    parallel_items = parsed.get("parallel_items") or []
    required_skills = parsed.get("required_skills") or {}
    preferred_skills = parsed.get("preferred_skills") or {}
    score = calculate_parallel_score(parallel_items)
    decision, reason = judge_proposal(score, required_skills)
    return {
        "parallel_items": parallel_items,
        "parallel_score": score,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "proposal_decision": decision,
        "proposal_reason": reason,
        "skill_memo": build_skill_memo(required_skills, preferred_skills, reason),
        "updated_at": date.today().isoformat(),
        "notes": parsed.get("notes", ""),
    }


def build_skill_memo(
    required_skills: dict[str, str],
    preferred_skills: dict[str, str],
    reason: str,
) -> str:
    lines = ["必須スキル:"]
    lines.extend(f"- {name}: {mark}" for name, mark in required_skills.items())
    lines.append("尚可スキル:")
    lines.extend(f"- {name}: {mark}" for name, mark in preferred_skills.items())
    lines.append(f"判定理由: {reason}")
    return "\n".join(lines)


def update_engineer_page(cfg: dict[str, str], page_id: str, result: dict[str, Any]) -> None:
    props = {
        "並行スコア": {"number": result["parallel_score"]},
        "スキル判定メモ": {"rich_text": [{"text": {"content": result["skill_memo"][:1900]}}]},
        "提案可否": {"select": {"name": result["proposal_decision"]}},
        "最終更新日": {"date": {"start": result["updated_at"]}},
    }
    res = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=notion_headers(required(cfg, "NOTION_API_KEY")),
        json={"properties": props},
        timeout=20,
    )
    res.raise_for_status()


def read_body(args: argparse.Namespace) -> str:
    if args.sample:
        return SAMPLE_PATH.read_text(encoding="utf-8")
    if args.input:
        return Path(args.input).read_text(encoding="utf-8")
    raise RuntimeError("--sample または --input を指定してください")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="返信メール本文を解析してNotionエンジニアDBへ反映します")
    parser.add_argument("--dry-run", action="store_true", help="Notion書き込みをスキップ")
    parser.add_argument("--sample", action="store_true", help="test_data/sample_reply.txtを解析")
    parser.add_argument("--input", help="解析するメール本文txtパス")
    parser.add_argument("--engineer-id", help="更新対象NotionページID")
    parser.add_argument("--engineer-name", help="エンジニア名でNotion DBを検索")
    parser.add_argument("--no-claude", action="store_true", help="Claude APIを使わずregexで解析")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config()
    body = read_body(args)
    result = analyze_reply(body, cfg, use_claude=not args.no_claude)

    log("[reply_parser] 解析結果")
    log(json.dumps(result, ensure_ascii=False, indent=2))

    if args.dry_run:
        log("[reply_parser] dry-runのためNotion書き込みをスキップ")
        return 0

    page = query_engineer_page(cfg, args.engineer_name, args.engineer_id)
    if not page:
        raise RuntimeError("更新対象エンジニアが見つかりません")
    update_engineer_page(cfg, page["id"], result)
    log(f"[reply_parser] Notion更新完了: {page['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
