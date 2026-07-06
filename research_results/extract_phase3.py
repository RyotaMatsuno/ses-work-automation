# -*- coding: utf-8 -*-
"""Phase 3: 求人ページテキスト取得 + CostGuard経由LLM構造化抽出"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from crawl_common import (
    BASE_DIR,
    SES_WORK_ROOT,
    USER_AGENT,
    log_error,
    read_csv,
    retry_call,
    today_str,
    write_csv,
)

if str(SES_WORK_ROOT) not in sys.path:
    sys.path.insert(0, str(SES_WORK_ROOT))

import cost_guard  # noqa: E402
from openai import OpenAI  # noqa: E402

OUT_JSONL = BASE_DIR / "phase3_extracted.jsonl"
OUT_CSV = BASE_DIR / "phase3_extracted.csv"
CHECKPOINT = BASE_DIR / "phase3_checkpoint.txt"

EXTRACTION_FIELDS = [
    "company_name",
    "employment_type",
    "base_salary_monthly",
    "incentive_description",
    "incentive_rate_pct",
    "incentive_base",
    "incentive_type",
    "incentive_cap",
    "expected_annual_min",
    "expected_annual_max",
    "has_quota",
    "required_experience",
    "employee_count",
    "founded_year",
    "hq_location",
    "remote_policy",
    "notes",
    "source_url",
    "crawl_date",
]

SYSTEM_PROMPT = """あなたは日本の求人票から報酬情報を抽出するアシスタントです。
以下の求人テキストから指定JSONフィールドを抽出してください。
情報がない場合はnull。推測はせず、明記されている情報のみ抽出。
インセンティブ率が明記されていない場合はincentive_rate_pct=null。
金額は整数（円）で出力。出力はJSONオブジェクト1件のみ、他のテキストは含めない。"""

USER_TEMPLATE = """以下の求人テキストから、次のフィールドを持つJSONを1件出力してください:
{fields}

求人URL: {url}

--- 求人テキスト ---
{text}
"""


def _load_env_client() -> OpenAI:
    env_path = SES_WORK_ROOT / "config" / ".env"
    api_key = ""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENAI_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not api_key:
        api_key = __import__("os").environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not found in config/.env")
    return OpenAI(api_key=api_key)


def _collect_source_urls() -> list[str]:
    urls: list[str] = []
    for path, field in [
        (BASE_DIR / "phase1_urls_dedup.csv", "result_url"),
        (BASE_DIR / "phase2_engage.csv", "job_url"),
        (BASE_DIR / "phase2_green.csv", "job_url"),
    ]:
        for row in read_csv(path):
            u = row.get(field, "").strip()
            if u and u not in urls:
                urls.append(u)
    return urls


def _load_checkpoint() -> set[str]:
    if not CHECKPOINT.exists():
        return set()
    return {line.strip() for line in CHECKPOINT.read_text(encoding="utf-8").splitlines() if line.strip()}


def _save_checkpoint(url: str) -> None:
    with CHECKPOINT.open("a", encoding="utf-8") as f:
        f.write(url + "\n")


def _fetch_page_text(page, url: str) -> str:
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2000)
    return page.inner_text("body")[:12000]


def _parse_json_response(content: str) -> dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("response is not a JSON object")
    data["source_url"] = data.get("source_url")
    data["crawl_date"] = today_str()
    return data


def _extract_with_llm(client: OpenAI, url: str, text: str) -> dict[str, Any]:
    target_id = re.sub(r"[^a-zA-Z0-9]", "_", url)[-120:]
    decision = cost_guard.allowed(
        phase="research",
        block_type="light",
        target_id=target_id,
        est_in=1200,
        est_out=400,
        model_hint="gpt-4.1-nano",
        script="extract_phase3",
    )
    if not decision.allowed:
        raise RuntimeError(f"CostGuard blocked: {decision.reason}")

    try:
        resp = client.chat.completions.create(
            model=decision.model or "gpt-4.1-nano",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": USER_TEMPLATE.format(
                        fields=json.dumps(EXTRACTION_FIELDS, ensure_ascii=False),
                        url=url,
                        text=text,
                    ),
                },
            ],
            temperature=0,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        in_tok = resp.usage.prompt_tokens if resp.usage else 0
        out_tok = resp.usage.completion_tokens if resp.usage else 0
        cost_guard.finalize(decision, in_tok, out_tok, success=True)
        parsed = _parse_json_response(content)
        parsed["source_url"] = url
        return parsed
    except Exception as e:
        cost_guard.finalize(decision, 0, 0, success=False, error_kind="transient")
        raise e


def run_extraction(rate_limit: float, limit: int) -> list[dict]:
    urls = _collect_source_urls()
    done = _load_checkpoint()
    pending = [u for u in urls if u not in done]
    if limit:
        pending = pending[:limit]

    print(f"URLs total={len(urls)} pending={len(pending)}")
    if not pending:
        return _load_jsonl_results()

    client = _load_env_client()
    results: list[dict] = _load_jsonl_results()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ja-JP", user_agent=USER_AGENT)
        page = context.new_page()

        for i, url in enumerate(pending, 1):
            try:
                text = retry_call(
                    lambda u=url: _fetch_page_text(page, u),
                    phase="phase3_fetch",
                    url=url,
                )
                # Phase2で既にraw_textがある場合は再利用
                if len(text) < 200:
                    for src in [BASE_DIR / "phase2_engage.csv", BASE_DIR / "phase2_green.csv"]:
                        for row in read_csv(src):
                            if row.get("job_url") == url and row.get("raw_text"):
                                text = row["raw_text"]
                                break

                row = retry_call(
                    lambda u=url, t=text: _extract_with_llm(client, u, t),
                    phase="phase3_llm",
                    url=url,
                )
                results.append(row)
                with OUT_JSONL.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                _save_checkpoint(url)
            except Exception as e:
                log_error("phase3", url, type(e).__name__, str(e))

            if i % 10 == 0:
                print(f"  processed {i}/{len(pending)}")
            if i % 100 == 0:
                print(f"  checkpoint at {i}")
            time.sleep(rate_limit)

        browser.close()

    return results


def _regex_extract(text: str, url: str) -> dict:
    """LLMなしのルールベース抽出（フォールバック）"""
    import re
    from crawl_common import today_str

    company = ""
    m_co = re.search(r"株式会社[^\s\n|｜]+|合同会社[^\s\n|｜]+", text)
    if m_co:
        company = m_co.group(0)

    employment = ""
    for kw in ["正社員", "契約社員", "業務委託", "派遣"]:
        if kw in text:
            employment = kw
            break

    base_monthly = None
    m_sal = re.search(r"月給\s*([\d,]+)\s*円", text)
    if m_sal:
        base_monthly = int(m_sal.group(1).replace(",", ""))

    incentive_desc = ""
    rate_pct = None
    for line in text.splitlines():
        if any(k in line for k in ["インセンティブ", "粗利", "歩合", "成果報酬", "還元"]):
            incentive_desc += line.strip() + " "
    m_rate = re.search(r"粗利[^\d]*(\d{1,2})\s*[％%]", incentive_desc or text)
    if m_rate:
        rate_pct = int(m_rate.group(1))

    incentive_base = "粗利" if "粗利" in incentive_desc else ("不明" if not incentive_desc else "不明")
    incentive_type = "ストック型" if "ストック" in text else ("フロー型" if "成約" in text else "不明")
    incentive_cap = "上限なし" if "上限なし" in text or "青天井" in text else "不明"

    annual_min = annual_max = None
    m_ann = re.search(r"想定年収\s*([\d,]+)\s*万[^\d]*([\d,]+)\s*万", text)
    if m_ann:
        annual_min = int(m_ann.group(1).replace(",", "")) * 10000
        annual_max = int(m_ann.group(2).replace(",", "")) * 10000

    has_quota = "なし" if "ノルマなし" in text else "不明"
    required = "未経験可" if "未経験" in text else ""
    remote = "フルリモート" if "フルリモート" in text else ("ハイブリッド" if "リモート" in text or "在宅" in text else "不明")

    return {
        "company_name": company,
        "employment_type": employment,
        "base_salary_monthly": base_monthly,
        "incentive_description": incentive_desc.strip()[:500],
        "incentive_rate_pct": rate_pct,
        "incentive_base": incentive_base,
        "incentive_type": incentive_type,
        "incentive_cap": incentive_cap,
        "expected_annual_min": annual_min,
        "expected_annual_max": annual_max,
        "has_quota": has_quota,
        "required_experience": required,
        "employee_count": None,
        "founded_year": None,
        "hq_location": "",
        "remote_policy": remote,
        "notes": "",
        "source_url": url,
        "crawl_date": today_str(),
    }


def run_rules_from_phase2() -> list[dict]:
    """phase2_engage.csv の raw_text からルールベース抽出"""
    from crawl_common import read_csv

    rows = []
    for r in read_csv(BASE_DIR / "phase2_engage.csv"):
        text = r.get("raw_text", "") or ""
        url = r.get("job_url", "")
        if not text or not url:
            continue
        item = _regex_extract(text, url)
        if r.get("company_name"):
            item["company_name"] = r["company_name"]
        rows.append(item)
    return rows


def _load_jsonl_results() -> list[dict]:
    if not OUT_JSONL.exists():
        return []
    rows: list[dict] = []
    for line in OUT_JSONL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate-limit", type=float, default=10.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--rules-only", action="store_true", help="LLMを使わずphase2/rawからルール抽出")
    args = parser.parse_args()

    if args.rules_only:
        rows = run_rules_from_phase2()
        n = write_csv(OUT_CSV, EXTRACTION_FIELDS, rows)
        print(f"phase3_extracted.csv (rules): {n} rows")
        return 0

    rows = run_extraction(args.rate_limit, args.limit)
    n = write_csv(OUT_CSV, EXTRACTION_FIELDS, rows)
    print(f"phase3_extracted.csv: {n} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
