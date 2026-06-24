# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values

PROP = {
    "name": "名前",
    "target_flag": "提案対象フラグ",
    "nationality": "国籍",
    "experience": "経験年数",
    "available_date": "稼働可能日",
    "remarks": "備考（LINEメモ）",
    "exclude_reason": "除外理由",
    "raw_info": "人員情報原文",
    "rate": "単価（万円）",
    "age": "年齢",
}

NATIONALITY_BLOCK = {"外国籍", "外国籍候補", "海外籍", "日本国籍以外"}
NATIONALITY_UNKNOWN = {"要確認", "不明", "未確認", "", None}

PLACEHOLDER_NAMES = {
    "名前",
    "氏名",
    "開発太郎",
    "開発 太郎",
    "山田太郎",
    "テスト",
    "test",
    "サンプル",
    "sample",
    "N/A",
    "不明",
    "人材",
    "エンジニア",
}

P6_HIGH_SIGNAL = [
    "案件名",
    "案件：",
    "■案件内容",
    "作業内容",
    "業務内容",
    "募集人数",
    "商流",
    "精算",
    "面談回数",
    "貴社まで",
    "契約期間",
    "契約形態",
]
P6_MEDIUM_SIGNAL = [
    "必要スキル：",
    "■担当工程：",
    "■必須スキル",
    "尚可スキル",
    "作業場所",
    "■単価：",
    "勤務地",
    "リモート頻度",
    "外国籍可否",
]

ALL_PATTERNS = ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]

NOTION_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR.parent / "config" / ".env"
OUTPUT_DIR = SCRIPT_DIR / "output"


def notion_request(method, url, headers, max_retries=5, **kwargs):
    for attempt in range(max_retries):
        res = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        if res.status_code == 429:
            retry_after = int(res.headers.get("Retry-After", "1"))
            time.sleep(retry_after + 0.5)
            continue
        if 500 <= res.status_code < 600:
            time.sleep(2**attempt)
            continue
        res.raise_for_status()
        return res
    raise RuntimeError(f"Notion API retry exhausted: {url}")


def load_env(db_id_override: str | None) -> tuple[str, str]:
    config = dotenv_values(ENV_PATH, encoding="utf-8")
    api_key = (config.get("NOTION_API_KEY") or "").strip()
    db_id = (db_id_override or config.get("NOTION_ENGINEER_DB_ID") or "").strip()
    if not api_key:
        raise SystemExit(f"[ERROR] NOTION_API_KEY が未設定です ({ENV_PATH})")
    if not db_id:
        raise SystemExit(f"[ERROR] NOTION_ENGINEER_DB_ID が未設定です ({ENV_PATH})")
    return api_key, db_id


def notion_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _title(prop: dict[str, Any] | None) -> str:
    return "".join(item.get("plain_text", "") for item in (prop or {}).get("title", []))


def _rich_text(prop: dict[str, Any] | None) -> str:
    return "".join(item.get("plain_text", "") for item in (prop or {}).get("rich_text", []))


def _select(prop: dict[str, Any] | None) -> str | None:
    value = (prop or {}).get("select")
    return value.get("name") if value else None


def _number(prop: dict[str, Any] | None) -> float | None:
    value = (prop or {}).get("number")
    return float(value) if value is not None else None


def _checkbox(prop: dict[str, Any] | None) -> bool:
    return bool((prop or {}).get("checkbox"))


def _date_start(prop: dict[str, Any] | None) -> date | None:
    value = (prop or {}).get("date")
    if not value or not value.get("start"):
        return None
    start = value["start"][:10]
    return datetime.strptime(start, "%Y-%m-%d").date()


def parse_page(props: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": _title(props.get(PROP["name"])),
        "target_flag": _checkbox(props.get(PROP["target_flag"])),
        "nationality": _select(props.get(PROP["nationality"])),
        "experience": _number(props.get(PROP["experience"])),
        "available_date": _date_start(props.get(PROP["available_date"])),
        "remarks": _rich_text(props.get(PROP["remarks"])),
        "exclude_reason": _rich_text(props.get(PROP["exclude_reason"])),
        "raw_info": _rich_text(props.get(PROP["raw_info"])),
        "rate": _number(props.get(PROP["rate"])),
        "age": _number(props.get(PROP["age"])),
    }


OPTIONAL_PROP_KEYS = {"age"}


def validate_schema(db_schema: dict[str, Any]) -> None:
    properties = db_schema.get("properties", {})
    missing = [PROP[key] for key in PROP if key not in OPTIONAL_PROP_KEYS and PROP[key] not in properties]
    if missing:
        print("[ERROR] Notion DBに以下のプロパティが存在しません:")
        for name in missing:
            print(f"  - {name}")
        raise SystemExit(1)
    if PROP["age"] not in properties:
        print(f"[WARN] オプション項目 {PROP['age']} がDBにありません（P3年齢整合チェックはスキップ）")


def fetch_database_schema(db_id: str, headers: dict[str, str]) -> dict[str, Any]:
    url = f"{NOTION_BASE}/databases/{db_id}"
    res = notion_request("GET", url, headers=headers)
    return res.json()


def fetch_all_pages(db_id: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        payload: dict[str, Any] = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        url = f"{NOTION_BASE}/databases/{db_id}/query"
        res = notion_request("POST", url, headers=headers, json=payload)
        data = res.json()
        pages.extend(data.get("results", []))
        time.sleep(0.35)
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return pages


def has_idempotency_marker(text: str, pattern: str) -> bool:
    return f"[cleaner:{pattern}:" in text


def has_exclude_prefix(text: str, prefix: str) -> bool:
    return prefix in text


def check_p1(data: dict[str, Any]) -> dict[str, Any] | None:
    if data["nationality"] not in NATIONALITY_BLOCK or not data["target_flag"]:
        return None
    if has_exclude_prefix(data["exclude_reason"], "P1:外国籍"):
        return None
    return {
        "pattern": "P1",
        "severity": "action",
        "message": "P1:外国籍（自動クレンジング）",
        "exclude_prefix": "P1:外国籍（自動クレンジング）",
        "set_flag_false": True,
    }


def check_p2(data: dict[str, Any]) -> dict[str, Any] | None:
    nationality = data["nationality"]
    if nationality not in NATIONALITY_UNKNOWN or not data["target_flag"]:
        return None
    if has_exclude_prefix(data["exclude_reason"], "P2:国籍要確認"):
        return None
    return {
        "pattern": "P2",
        "severity": "action",
        "message": "P2:国籍要確認（要人工確認）",
        "exclude_prefix": "P2:国籍要確認（要人工確認）",
        "set_flag_false": True,
    }


def check_p3(data: dict[str, Any], today: date) -> list[dict[str, Any]]:
    _ = today
    findings: list[dict[str, Any]] = []
    if has_idempotency_marker(data["remarks"], "P3"):
        return findings

    exp = data["experience"]
    if exp is None:
        return findings

    nullify = False
    warning_only = False
    reason = ""

    if exp < 0:
        nullify = True
        reason = f"経験年数異常値 {exp} をnull化"
    elif exp > 45:
        nullify = True
        reason = f"経験年数異常値 {exp} をnull化"
    elif 36 <= exp <= 45:
        warning_only = True
        reason = f"経験年数 {exp} は要確認（36〜45）"

    age = data["age"]
    if age is not None and exp > age - 15:
        nullify = True
        warning_only = False
        reason = f"経験年数異常値 {exp} をnull化（年齢{age}と不整合）"

    if nullify:
        stamp = today.isoformat()
        findings.append(
            {
                "pattern": "P3",
                "severity": "action",
                "message": reason,
                "nullify_experience": True,
                "remarks_suffix": f"\n[cleaner:P3:{stamp}] {reason}",
            }
        )
    elif warning_only:
        findings.append(
            {
                "pattern": "P3",
                "severity": "warning",
                "message": reason,
            }
        )
    return findings


def check_p4(data: dict[str, Any], today: date) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if has_idempotency_marker(data["remarks"], "P4"):
        return findings

    avail = data["available_date"]
    if avail is None:
        return findings

    nullify = False
    warning_only = False
    reason = ""

    if avail < today - timedelta(days=180):
        nullify = True
        reason = f"稼働可能日異常値 {avail.isoformat()} をnull化"
    elif avail > today + timedelta(days=365):
        warning_only = True
        reason = f"稼働可能日 {avail.isoformat()} は未来すぎる（要確認）"

    if nullify:
        stamp = today.isoformat()
        findings.append(
            {
                "pattern": "P4",
                "severity": "action",
                "message": reason,
                "nullify_available_date": True,
                "remarks_suffix": f"\n[cleaner:P4:{stamp}] {reason}",
            }
        )
    elif warning_only:
        findings.append(
            {
                "pattern": "P4",
                "severity": "warning",
                "message": reason,
            }
        )
    return findings


def check_p5(data: dict[str, Any]) -> dict[str, Any] | None:
    name = (data["name"] or "").strip()
    if not name:
        return None

    matched = name in PLACEHOLDER_NAMES
    keywords = ("案件", "募集", "株式会社", "要員情報")
    if not matched:
        matched = any(kw in name for kw in keywords)

    if not matched or not data["target_flag"]:
        return None
    if has_exclude_prefix(data["exclude_reason"], "P5:プレースホルダ名"):
        return None
    return {
        "pattern": "P5",
        "severity": "action",
        "message": "P5:プレースホルダ名（要確認）",
        "exclude_prefix": "P5:プレースホルダ名（要確認）",
        "set_flag_false": True,
    }


def check_p6(data: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if has_idempotency_marker(data["exclude_reason"], "P6") or has_exclude_prefix(
        data["exclude_reason"], "P6:案件メール"
    ):
        return findings

    text = (data["remarks"] or "") + (data["raw_info"] or "")
    high_count = sum(1 for s in P6_HIGH_SIGNAL if s in text)
    medium_count = sum(1 for s in P6_MEDIUM_SIGNAL if s in text)
    score = high_count * 2 + medium_count

    if score <= 1:
        return findings
    if 2 <= score <= 3:
        findings.append(
            {
                "pattern": "P6",
                "severity": "warning",
                "message": f"P6:案件メール疑い（score={score}）",
                "score": score,
            }
        )
        return findings

    msg = f"P6:案件メール誤登録（score={score}）"
    findings.append(
        {
            "pattern": "P6",
            "severity": "action",
            "message": msg,
            "exclude_prefix": msg,
            "set_flag_false": True,
            "score": score,
        }
    )
    return findings


def check_p7(data: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    rate = data["rate"]
    if rate is None and data["target_flag"]:
        findings.append(
            {
                "pattern": "P7",
                "severity": "warning",
                "message": "P7:単価未設定かつ提案対象フラグ=True",
            }
        )
    if rate is not None and (rate < 20 or rate > 150):
        findings.append(
            {
                "pattern": "P7",
                "severity": "warning",
                "message": f"P7:単価異常値疑い（{rate}万円）",
            }
        )
    return findings


def run_checks(page: dict[str, Any], patterns: set[str], today: date) -> list[dict[str, Any]]:
    props = page.get("properties", {})
    data = parse_page(props)
    findings: list[dict[str, Any]] = []

    if "P1" in patterns:
        f = check_p1(data)
        if f:
            findings.append(f)
    if "P2" in patterns:
        f = check_p2(data)
        if f:
            findings.append(f)
    if "P3" in patterns:
        findings.extend(check_p3(data, today))
    if "P4" in patterns:
        findings.extend(check_p4(data, today))
    if "P5" in patterns:
        f = check_p5(data)
        if f:
            findings.append(f)
    if "P6" in patterns:
        findings.extend(check_p6(data))
    if "P7" in patterns:
        findings.extend(check_p7(data))

    for finding in findings:
        finding["page_id"] = page.get("id", "")
        finding["name"] = data["name"]
        finding["parsed"] = data
    return findings


def prepend_text(existing: str, prefix: str) -> str:
    existing = existing or ""
    if not existing.strip():
        return prefix
    return f"{prefix}\n{existing}"


def append_text(existing: str, suffix: str) -> str:
    existing = existing or ""
    return existing + suffix


def rich_text_payload(content: str) -> dict[str, Any]:
    return {"rich_text": [{"type": "text", "text": {"content": content[:2000]}}]}


def build_update_payload(page: dict[str, Any], action_findings: list[dict[str, Any]]) -> dict[str, Any]:
    props = page.get("properties", {})
    data = parse_page(props)
    properties: dict[str, Any] = {}

    exclude_reason = data["exclude_reason"]
    remarks = data["remarks"]
    set_flag_false = False
    nullify_experience = False
    nullify_available_date = False

    for finding in action_findings:
        if finding.get("set_flag_false"):
            set_flag_false = True
        if finding.get("exclude_prefix"):
            exclude_reason = prepend_text(exclude_reason, finding["exclude_prefix"])
        if finding.get("remarks_suffix"):
            remarks = append_text(remarks, finding["remarks_suffix"])
        if finding.get("nullify_experience"):
            nullify_experience = True
        if finding.get("nullify_available_date"):
            nullify_available_date = True

    if set_flag_false:
        properties[PROP["target_flag"]] = {"checkbox": False}
    if exclude_reason != data["exclude_reason"]:
        properties[PROP["exclude_reason"]] = rich_text_payload(exclude_reason)
    if remarks != data["remarks"]:
        properties[PROP["remarks"]] = rich_text_payload(remarks)
    if nullify_experience:
        properties[PROP["experience"]] = {"number": None}
    if nullify_available_date:
        properties[PROP["available_date"]] = {"date": None}

    return {"properties": properties}


def write_backup(path: Path, pages: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for page in pages:
            record = {
                "page_id": page.get("id"),
                "properties": page.get("properties", {}),
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_reports(
    txt_path: Path,
    json_path: Path,
    *,
    live: bool,
    patterns: list[str],
    all_findings: list[dict[str, Any]],
    counts: dict[str, dict[str, int]],
    update_stats: dict[str, int],
) -> None:
    mode = "live" if live else "dry_run"
    lines = [
        f"エンジニアDBクレンジングレポート ({mode})",
        f"実行日時: {datetime.now().isoformat(timespec='seconds')}",
        f"パターン: {','.join(patterns)}",
        "",
        "=== 検出件数 ===",
    ]
    for p in patterns:
        c = counts.get(p, {"action": 0, "warning": 0})
        lines.append(f"  {p}: action={c['action']}, warning={c['warning']}")

    lines.extend(
        [
            "",
            "=== 更新サマリー ===",
            f"  成功: {update_stats.get('success', 0)}",
            f"  失敗: {update_stats.get('fail', 0)}",
            f"  上限スキップ: {update_stats.get('skipped_limit', 0)}",
            "",
            "=== 詳細 ===",
        ]
    )

    for finding in all_findings:
        prefix = "[DRY-RUN] " if not live and finding["severity"] == "action" else ""
        lines.append(
            f"{prefix}{finding['pattern']} [{finding['severity']}] "
            f"{finding.get('name', '')} ({finding.get('page_id', '')}): "
            f"{finding.get('message', '')}"
        )

    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report_json = {
        "mode": mode,
        "patterns": patterns,
        "counts": counts,
        "update_stats": update_stats,
        "findings": [
            {
                "pattern": f["pattern"],
                "severity": f["severity"],
                "page_id": f.get("page_id"),
                "name": f.get("name"),
                "message": f.get("message"),
            }
            for f in all_findings
        ],
    }
    json_path.write_text(json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_patterns(raw: str | None) -> list[str]:
    if not raw:
        return list(ALL_PATTERNS)
    patterns = [p.strip().upper() for p in raw.split(",") if p.strip()]
    invalid = [p for p in patterns if p not in ALL_PATTERNS]
    if invalid:
        raise SystemExit(f"[ERROR] 不明なパターン: {', '.join(invalid)}")
    return patterns


def main() -> int:
    parser = argparse.ArgumentParser(description="エンジニアDB品質クレンジング")
    parser.add_argument("--live", action="store_true", help="Notionを実際に更新")
    parser.add_argument("--patterns", type=str, help="実行パターン (例: P1,P2,P5)")
    parser.add_argument("--max-updates", type=int, default=50, help="1回の最大更新件数 (デフォルト: 50)")
    parser.add_argument("--db-id", type=str, help="エンジニアDB ID上書き")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    patterns = parse_patterns(args.patterns)
    pattern_set = set(patterns)
    today = date.today()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    api_key, db_id = load_env(args.db_id)
    headers = notion_headers(api_key)

    prefix = "" if args.live else "[DRY-RUN] "
    print(f"{prefix}モード: {'live' if args.live else 'dry_run'}")
    print(f"{prefix}パターン: {','.join(patterns)}")

    print("DBスキーマを取得中...")
    schema = fetch_database_schema(db_id, headers)
    validate_schema(schema)

    print("全件取得中...")
    pages = fetch_all_pages(db_id, headers)
    print(f"取得件数: {len(pages)}")

    all_findings: list[dict[str, Any]] = []
    counts: dict[str, dict[str, int]] = {p: {"action": 0, "warning": 0} for p in patterns}

    page_findings: dict[str, list[dict[str, Any]]] = {}
    for page in pages:
        findings = run_checks(page, pattern_set, today)
        if not findings:
            continue
        page_id = page.get("id", "")
        page_findings[page_id] = findings
        all_findings.extend(findings)
        for f in findings:
            sev = f["severity"]
            p = f["pattern"]
            if p in counts:
                counts[p][sev] += 1

    action_pages: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for page in pages:
        page_id = page.get("id", "")
        findings = page_findings.get(page_id, [])
        action_findings = [f for f in findings if f["severity"] == "action"]
        if action_findings:
            action_pages.append((page, action_findings))

    backup_path = OUTPUT_DIR / f"backup_{ts}.jsonl"
    if action_pages:
        write_backup(backup_path, [p for p, _ in action_pages])
        print(f"バックアップ: {backup_path} ({len(action_pages)}件)")
    else:
        print("バックアップ対象なし（action検出0件）")

    update_stats = {"success": 0, "fail": 0, "skipped_limit": 0}
    remaining_due_to_limit = 0

    if action_pages:
        print(f"{prefix}action対象: {len(action_pages)}件")
        for idx, (page, action_findings) in enumerate(action_pages):
            page_id = page.get("id", "")
            name = parse_page(page.get("properties", {}))["name"]
            patterns_hit = ",".join(sorted({f["pattern"] for f in action_findings}))

            if args.live:
                if update_stats["success"] >= args.max_updates:
                    remaining_due_to_limit += 1
                    update_stats["skipped_limit"] += 1
                    continue
                payload = build_update_payload(page, action_findings)
                if not payload["properties"]:
                    continue
                try:
                    url = f"{NOTION_BASE}/pages/{page_id}"
                    notion_request("PATCH", url, headers=headers, json=payload)
                    time.sleep(0.5)
                    update_stats["success"] += 1
                    print(f"[LIVE] 更新成功: {name} ({page_id}) [{patterns_hit}]")
                except Exception as e:
                    update_stats["fail"] += 1
                    print(f"[ERROR] 更新失敗: {name} ({page_id}): {e}")
            else:
                print(f"{prefix}検出: {name} ({page_id}) [{patterns_hit}] - {len(action_findings)} action")

    if remaining_due_to_limit:
        print(f"[WARN] --max-updates {args.max_updates} に達しました。未更新: {remaining_due_to_limit}件")

    for p in patterns:
        c = counts[p]
        print(f"{prefix}{p}: action={c['action']}, warning={c['warning']}")

    if args.live:
        print(
            f"更新サマリー: 成功={update_stats['success']}, "
            f"失敗={update_stats['fail']}, "
            f"上限スキップ={update_stats['skipped_limit']}"
        )

    report_txt = OUTPUT_DIR / f"report_{ts}.txt"
    report_json = OUTPUT_DIR / f"report_{ts}.json"
    write_reports(
        report_txt,
        report_json,
        live=args.live,
        patterns=patterns,
        all_findings=all_findings,
        counts=counts,
        update_stats=update_stats,
    )
    print(f"レポート: {report_txt}")
    print(f"レポート: {report_json}")

    print("次は python cleaner.py --live 実行前に output/ のレポートを確認してください")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
