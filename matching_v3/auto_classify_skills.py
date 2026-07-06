"""Phase 2B: Notion案件DBから全スキル値を収集し自動分類 (dry-run)。

Usage:
    python matching_v3/auto_classify_skills.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from script_bootstrap import bootstrap

BASE_DIR, SES_WORK = bootstrap()

import requests
from dotenv import dotenv_values

from mail_pipeline.skill_extractor import (
    normalize_skill_text,
    strip_business_suffix,
    validate_skill,
)

ENV_PATH = SES_WORK / "config" / ".env"
ALIASES_PATH = BASE_DIR / "skill_aliases.json"
RESEARCH_DIR = SES_WORK / "research_results"
CASE_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1/"
GPT_MODEL = "gpt-4.1-nano"
BATCH_SIZE = 100
COST_LIMIT_USD = 2.0  # Phase 4B: $2超で中断

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _load_env() -> dict[str, str]:
    env = dict(dotenv_values(ENV_PATH, encoding="utf-8"))
    env.update({k: v for k, v in os.environ.items() if v})
    return env


def _load_aliases() -> dict[str, str]:
    data = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
    return {k.lower(): v for k, v in data.get("aliases", {}).items()}


def _query_all_cases(token: str) -> list[dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    results: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        body: dict[str, Any] = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        resp = requests.post(
            NOTION_BASE + f"databases/{CASE_DB_ID}/query",
            headers=headers,
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))
        cursor = data.get("next_cursor")
        if not data.get("has_more") or not cursor:
            break
        time.sleep(0.3)
    return results


def _extract_skills_from_pages(pages: list[dict]) -> Counter:
    counter: Counter = Counter()
    for page in pages:
        props = page.get("properties", {})
        for field in ("必要スキル", "尚可スキル"):
            ms = props.get(field, {})
            if ms and ms.get("type") == "multi_select":
                for item in ms.get("multi_select", []):
                    name = item.get("name", "").strip()
                    if name:
                        counter[name] += 1
    return counter


def _classify_rule_based(
    skill: str, aliases: dict[str, str]
) -> tuple[str, str | None]:
    """Returns (class, canonical_form | None).

    class: 'canonical' | 'canonical_cleaned' | 'garbage' | 'unknown'
    """
    norm = normalize_skill_text(skill)
    if not validate_skill(norm)[0]:
        stripped = strip_business_suffix(norm)
        if stripped and stripped != norm and validate_skill(stripped)[0]:
            alias_hit = aliases.get(stripped.lower())
            return "canonical_cleaned", alias_hit or stripped
        return "garbage", None

    alias_hit = aliases.get(norm.lower())
    if alias_hit:
        return "canonical", alias_hit

    stripped = strip_business_suffix(norm)
    if stripped and stripped != norm:
        alias_hit = aliases.get(stripped.lower())
        if alias_hit:
            return "canonical_cleaned", alias_hit

    return "unknown", None


def _gpt_classify_batch(
    items: list[tuple[str, int]], client: Any, total_cost: list[float]
) -> list[dict[str, Any]]:
    """items: list of (skill_name, count). Returns classification results."""
    prompt_lines = [f"{i+1}. {name} (使用回数: {cnt})" for i, (name, cnt) in enumerate(items)]
    system_msg = (
        "あなたはITスキル分類専門家です。以下のスキル値リストを分類してください。\n"
        "各スキルについてJSON配列で返してください。各要素は:\n"
        '{"index": N, "class": "tech_skill|role|process|garbage|unknown", '
        '"canonical_form": "正規化された名前またはnull", "confidence": 0.0-1.0}\n'
        "class定義:\n"
        "- tech_skill: プログラミング言語・フレームワーク・インフラ技術\n"
        "- role: 職種・役割 (PM, PL, SE等)\n"
        "- process: 工程 (要件定義, 設計等)\n"
        "- garbage: 無効な値（記号、文章、無関係の語）\n"
        "- unknown: 判断できない\n"
        "canonical_formは正規化された表記（例: 'react' → 'React'）。garbageはnull。\n"
        "応答はJSONのみ（```なし）。"
    )
    user_msg = "\n".join(prompt_lines)

    est_input = len(system_msg) // 3 + len(user_msg) // 3
    est_output = len(items) * 30
    est_cost = (est_input * 0.10 + est_output * 0.40) / 1_000_000

    if total_cost[0] + est_cost > COST_LIMIT_USD:
        logger.warning("GPTコスト上限 $%.2f 超過予測 - バッチスキップ", COST_LIMIT_USD)
        return []

    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0,
            max_tokens=est_output * 3,
        )
        actual_input = response.usage.prompt_tokens
        actual_output = response.usage.completion_tokens
        actual_cost = (actual_input * 0.10 + actual_output * 0.40) / 1_000_000
        total_cost[0] += actual_cost
        logger.info(
            "GPT batch %d items, cost $%.4f (total $%.4f)",
            len(items),
            actual_cost,
            total_cost[0],
        )
        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)
        return parsed if isinstance(parsed, list) else []
    except Exception as exc:
        logger.error("GPT classify error: %s", exc)
        return []


def run(dry_run: bool = True) -> None:
    env = _load_env()
    notion_token = env.get("NOTION_API_KEY", "")
    openai_key = env.get("OPENAI_API_KEY", "")
    if not notion_token:
        logger.error("NOTION_API_KEY not set")
        sys.exit(1)

    logger.info("Notion案件DB全件取得中...")
    pages = _query_all_cases(notion_token)
    logger.info("%d 案件を取得", len(pages))

    skill_counter = _extract_skills_from_pages(pages)
    logger.info("ユニークスキル値: %d 件", len(skill_counter))

    aliases = _load_aliases()
    all_results: list[dict[str, Any]] = []
    unknown_items: list[tuple[str, int]] = []

    for skill, count in skill_counter.most_common():
        cls, canonical = _classify_rule_based(skill, aliases)
        all_results.append(
            {
                "skill": skill,
                "count": count,
                "class": cls,
                "canonical_form": canonical,
                "source": "rule",
            }
        )
        if cls == "unknown":
            unknown_items.append((skill, count))

    logger.info(
        "ルールベース: canonical=%d, canonical_cleaned=%d, garbage=%d, unknown=%d",
        sum(1 for r in all_results if r["class"] == "canonical"),
        sum(1 for r in all_results if r["class"] == "canonical_cleaned"),
        sum(1 for r in all_results if r["class"] == "garbage"),
        len(unknown_items),
    )

    # GPT batch for unknowns
    if unknown_items and openai_key:
        import openai

        client = openai.OpenAI(api_key=openai_key)
        total_cost: list[float] = [0.0]

        for i in range(0, len(unknown_items), BATCH_SIZE):
            batch = unknown_items[i : i + BATCH_SIZE]
            logger.info("GPTバッチ %d-%d / %d", i + 1, i + len(batch), len(unknown_items))
            gpt_results = _gpt_classify_batch(batch, client, total_cost)
            if not gpt_results:
                break
            gpt_map = {r["index"]: r for r in gpt_results}
            for j, (skill, count) in enumerate(batch):
                gpt_r = gpt_map.get(j + 1, {})
                for existing in all_results:
                    if existing["skill"] == skill and existing["class"] == "unknown":
                        existing["class"] = gpt_r.get("class", "unknown")
                        existing["canonical_form"] = gpt_r.get("canonical_form")
                        existing["confidence"] = gpt_r.get("confidence", 0.0)
                        existing["source"] = "gpt"
                        break
            time.sleep(0.5)
    elif unknown_items:
        logger.warning("OPENAI_API_KEY未設定 - GPT分類スキップ (%d件)", len(unknown_items))

    today = date.today().strftime("%Y%m%d")
    RESEARCH_DIR.mkdir(exist_ok=True)

    # File 1: 全結果
    out_all = RESEARCH_DIR / f"skill_classified_{today}.json"
    out_all.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # File 2: 辞書追加候補（tech_skill / role / process で辞書未登録かつ confidence > 0.7）
    add_candidates = [
        r for r in all_results
        if r["class"] in ("tech_skill", "role", "process", "unknown")
        and r.get("source") == "gpt"
        and r.get("confidence", 0.0) >= 0.7
        and r.get("canonical_form")
    ]
    out_candidates = RESEARCH_DIR / f"skill_add_candidates_{today}.json"
    out_candidates.write_text(
        json.dumps(add_candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # File 3: 人間レビュー必要分（confidence < 0.7 またはclass=unknown）
    review_queue = [
        r for r in all_results
        if r.get("source") == "gpt"
        and (r.get("confidence", 0.0) < 0.7 or r["class"] == "unknown")
    ]
    # + rule-based unknowns with no GPT result
    review_queue += [
        r for r in all_results
        if r["class"] == "unknown" and r.get("source") == "rule"
    ]
    out_review = RESEARCH_DIR / f"skill_review_queue_{today}.json"
    out_review.write_text(
        json.dumps(review_queue, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    logger.info("=== 分類レポート ===")
    logger.info("全結果: %s (%d件)", out_all, len(all_results))
    logger.info("辞書追加候補: %s (%d件)", out_candidates, len(add_candidates))
    logger.info("レビューキュー: %s (%d件)", out_review, len(review_queue))
    if dry_run:
        logger.info("[dry-run] skill_aliases.json への書き込みはスキップしました")


if __name__ == "__main__":
    run(dry_run=True)
