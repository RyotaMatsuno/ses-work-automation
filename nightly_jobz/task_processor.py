"""タスク種別ごとの処理."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from nightly_jobz import config
from nightly_jobz.notion_queue import QueueTask, update_task_status

logger = logging.getLogger("nightly_jobz.processor")
JST = timezone(timedelta(hours=9))

STUB_TYPES = frozenset({"draft_intent", "draft_proposal", "matching"})
REVIEW_STUB_TYPES = frozenset({"review", "other"})


@dataclass
class ProcessResult:
    task_id: str
    task_type: str
    title: str
    status: str
    result_path: str = ""
    note: str = ""
    cost_usd: float = 0.0


def _target_id(task: QueueTask) -> str:
    raw = f"{task.page_id}:{task.task_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[\u3040-\u30ff\u4e00-\u9fffA-Za-z0-9]{2,}", text or "")
    seen: set[str] = set()
    keywords: list[str] = []
    for word in words:
        lower = word.lower()
        if lower in seen:
            continue
        seen.add(lower)
        keywords.append(word)
        if len(keywords) >= 12:
            break
    return keywords


def _estimate_gpt_cost(in_tokens: int, out_tokens: int) -> float:
    return in_tokens * 1.25 / 1_000_000 + out_tokens * 10 / 1_000_000


def call_gpt54(
    prompt: str,
    *,
    phase: str,
    target_id: str,
    dry_run: bool,
    run_cost: config.RunCostTracker,
) -> tuple[str, float]:
    if dry_run:
        logger.info("[DRY_RUN] GPT skip phase=%s target=%s", phase, target_id)
        return f"[DRY_RUN] GPT response for {phase}", 0.0

    if not run_cost.can_spend(0.05):
        raise RuntimeError(f"nightly budget exceeded (${run_cost.total_usd:.4f})")

    import sys

    if str(config.SES_WORK) not in sys.path:
        sys.path.insert(0, str(config.SES_WORK))
    from cost_guard import allowed, finalize
    from openai import OpenAI

    decision = allowed(
        phase=phase,
        block_type=config.BLOCK_TYPE,
        target_id=target_id,
        est_in=len(prompt) // 4 + 200,
        est_out=8000,
        model_hint=config.GPT_MODEL,
        script="nightly_jobz",
    )
    if decision.exit_code != 0:
        raise RuntimeError(f"CostGuard blocked: {decision.reason}")

    error_kind = ""
    in_tok = 0
    out_tok = 0
    text = ""
    try:
        client = OpenAI()
        resp = client.responses.create(
            model=config.GPT_MODEL,
            input=[{"role": "user", "content": prompt}],
            reasoning={"effort": "low"},
            max_output_tokens=8000,
        )
        for item in resp.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        text += content.text
        usage = resp.usage
        in_tok = int(getattr(usage, "input_tokens", 0) or 0)
        out_tok = int(getattr(usage, "output_tokens", 0) or 0)
        cost = _estimate_gpt_cost(in_tok, out_tok)
        run_cost.add(cost)
        return text, cost
    except Exception:
        error_kind = "transient"
        raise
    finally:
        if decision.allowed:
            finalize(
                decision,
                in_tokens=in_tok,
                out_tokens=out_tok,
                success=(error_kind == ""),
                error_kind=error_kind,
            )


def _save_markdown(path: Path, header: str, body: str, dry_run: bool) -> str:
    try:
        rel = path.relative_to(config.SES_WORK).as_posix()
    except ValueError:
        rel = path.as_posix()
    if dry_run:
        logger.info("[DRY_RUN] would save: %s", rel)
        return rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{header}\n\n---\n\n{body}", encoding="utf-8")
    logger.info("saved: %s", rel)
    return rel


def process_investigation(task: QueueTask, *, dry_run: bool, run_cost: config.RunCostTracker) -> ProcessResult:
    keywords = _extract_keywords(task.input_data)
    prompt = (
        "あなたはSES事業の調査アシスタントです。以下の調査依頼について、"
        "事実ベースで簡潔に調査結果をまとめてください。\n\n"
        f"タスクID: {task.task_id}\n"
        f"キーワード: {', '.join(keywords) if keywords else 'なし'}\n\n"
        f"依頼内容:\n{task.input_data[:8000]}"
    )
    text, cost = call_gpt54(
        prompt,
        phase="nightly_investigate",
        target_id=_target_id(task),
        dry_run=dry_run,
        run_cost=run_cost,
    )
    date_str = datetime.now(JST).strftime("%Y%m%d")
    safe_id = re.sub(r"[^\w\-]+", "_", task.task_id)[:40]
    out_path = config.RESEARCH_DIR / f"nightly_{safe_id}_{date_str}.md"
    header = f"# 調査結果: {task.task_id}\n\n日時: {datetime.now(JST).isoformat()}\nmodel: {config.GPT_MODEL}"
    rel_path = _save_markdown(out_path, header, text, dry_run=dry_run)

    update_task_status(
        task.page_id,
        "done",
        result_path=rel_path,
        dry_run=dry_run,
    )
    return ProcessResult(
        task_id=task.task_id,
        task_type="investigation",
        title=task.task_id,
        status="done",
        result_path=rel_path,
        cost_usd=cost,
    )


def process_spec_design(task: QueueTask, *, dry_run: bool, run_cost: config.RunCostTracker) -> ProcessResult:
    prompt = (
        "あなたはSES事業のシステム設計レビュアーです。devil's advocateの視点で"
        "以下の要件をレビューし、SPEC.mdドラフトをMarkdownで出力してください。\n\n"
        f"タスクID: {task.task_id}\n\n"
        f"要件:\n{task.input_data[:8000]}"
    )
    text, cost = call_gpt54(
        prompt,
        phase="nightly_spec_design",
        target_id=_target_id(task),
        dry_run=dry_run,
        run_cost=run_cost,
    )
    date_str = datetime.now(JST).strftime("%Y%m%d")
    safe_id = re.sub(r"[^\w\-]+", "_", task.task_id)[:40]
    out_path = config.DRAFTS_DIR / f"{safe_id}_{date_str}_SPEC.md"
    header = f"# SPECドラフト: {task.task_id}\n\n日時: {datetime.now(JST).isoformat()}\nmodel: {config.GPT_MODEL}"
    rel_path = _save_markdown(out_path, header, text, dry_run=dry_run)

    note = f"SPECドラフト生成: {rel_path}（松野確認待ち）"
    update_task_status(task.page_id, "review", dry_run=dry_run)
    return ProcessResult(
        task_id=task.task_id,
        task_type="spec_design",
        title=task.task_id,
        status="review",
        result_path=rel_path,
        note="松野確認: SPECドラフトレビュー",
        cost_usd=cost,
    )


def process_stub_blocked(task: QueueTask, *, dry_run: bool) -> ProcessResult:
    logger.info("[STUB] %s -> blocked (Phase 1未対応)", task.task_type)
    if not dry_run:
        update_task_status(task.page_id, "blocked", dry_run=False)
    return ProcessResult(
        task_id=task.task_id,
        task_type=task.task_type,
        title=task.task_id,
        status="blocked",
        note=f"Phase1未対応: {task.task_type}",
    )


def process_stub_review(task: QueueTask) -> ProcessResult:
    logger.info("[STUB] %s -> queued維持", task.task_type)
    return ProcessResult(
        task_id=task.task_id,
        task_type=task.task_type,
        title=task.task_id,
        status="queued",
        note="Phase1: review種別は手動対応",
    )


def dispatch_task(task: QueueTask, *, dry_run: bool, run_cost: config.RunCostTracker) -> ProcessResult:
    task_type = (task.task_type or "other").strip()
    if task_type == "investigation":
        return process_investigation(task, dry_run=dry_run, run_cost=run_cost)
    if task_type == "spec_design":
        return process_spec_design(task, dry_run=dry_run, run_cost=run_cost)
    if task_type in STUB_TYPES:
        return process_stub_blocked(task, dry_run=dry_run)
    if task_type in REVIEW_STUB_TYPES:
        return process_stub_review(task)
    return process_stub_blocked(task, dry_run=dry_run)
