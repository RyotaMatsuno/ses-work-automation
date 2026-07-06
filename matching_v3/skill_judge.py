# -*- coding: utf-8 -*-
"""
matching_v3/skill_judge.py - Anthropic API によるスキル判定。
cost_guard v2 の allowed()/finalize() を経由して全 LLM 呼び出しを管理する。
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from threading import Lock

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

from anthropic import Anthropic, AuthenticationError, BadRequestError, NotFoundError, RateLimitError

from cost_guard import Decision
from cost_guard import allowed as _cg_allowed
from cost_guard import finalize as _cg_finalize

BLOCK_TYPE = "skill_judge"
PHASE = "research"

VALID_RESULTS = {"◯", "×", "△"}
NEVER_MERGE: tuple[frozenset[str], ...] = (
    frozenset({"Java", "JavaScript"}),
    frozenset({"C", "C++", "C#", "Objective-C", "C言語"}),
    frozenset({"PM", "PMO"}),
    frozenset({"AWS", "Azure", "GCP"}),
    frozenset({"React", "React Native"}),
    frozenset({"SQL", "MySQL", "PostgreSQL", "SQL Server"}),
)
_NEVER_MERGE_LOOKUP: dict[str, frozenset[str]] = {}
for group in NEVER_MERGE:
    for skill in group:
        _NEVER_MERGE_LOOKUP[skill.lower()] = group

SYSTEM_PROMPT = """
あなたはSES案件のスキルマッチング担当です。
案件側のスキル要件ごとに、エンジニアのスキルリストで満たせるか判定してください。

判定ルール:
- "◯": 表記ゆれ、関連フレームワーク、明確な実務経験から満たすと判断できる
- "△": 基礎のみ、部分経験、近いが実務確認が必要
- "×": 経験が見当たらない、または要件を満たす根拠がない

同義語展開の禁止（絶対に混同しない）:
- Java と JavaScript は別スキル
- C / C++ / C# / Objective-C は別スキル
- PM と PMO は別スキル
- AWS / Azure / GCP は別スキル
- React と React Native は別スキル

必ずJSONオブジェクトだけを返してください。説明文やMarkdownは不要です。
値は result と reason を持つオブジェクトにしてください。
""".strip()


def _canonical_for_never_merge(skill: str) -> str:
    text = str(skill).strip()
    if not text:
        return ""
    lowered = text.lower()
    group = _NEVER_MERGE_LOOKUP.get(lowered)
    if group:
        for member in group:
            if member.lower() == lowered:
                return member
    return text


def skills_must_not_merge(skill_a: str, skill_b: str) -> bool:
    """同義語展開してはいけないスキル同士か判定する。"""
    left = _canonical_for_never_merge(skill_a)
    right = _canonical_for_never_merge(skill_b)
    if not left or not right or left.lower() == right.lower():
        return False
    left_group = _NEVER_MERGE_LOOKUP.get(left.lower())
    right_group = _NEVER_MERGE_LOOKUP.get(right.lower())
    return left_group is not None and left_group is right_group


def filter_confusable_skill_matches(required_skill: str, engineer_skills: list[str]) -> list[str]:
    """NEVER_MERGE 対象と混同する候補を除外したエンジニアスキル一覧を返す。"""
    return [
        skill
        for skill in engineer_skills
        if not skills_must_not_merge(required_skill, skill)
    ]

_REQUEST_LOCK = Lock()
_NEXT_REQUEST_AT = 0.0
MIN_REQUEST_INTERVAL_SECONDS = float(os.environ.get("ANTHROPIC_MIN_INTERVAL_SECONDS", "1.4"))


def _normalize_skill_list(skills) -> list[str]:
    if not skills:
        return []
    return [str(s).strip() for s in skills if str(s).strip()]


def _extract_text(response) -> str:
    texts = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            texts.append(text)
    return "\n".join(texts).strip()


def _parse_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _validate_result(required_skills: list[str], data: dict) -> dict:
    normalized = {}
    for skill in required_skills:
        item = data.get(skill, {})
        result = str(item.get("result", "×")).strip()
        reason = str(item.get("reason", "判定結果が不正です")).strip()
        if result not in VALID_RESULTS:
            result = "×"
            reason = "判定結果が◯/×/△以外だったため除外扱いにしました"
        normalized[skill] = {"result": result, "reason": reason}
    return normalized


def _wait_for_rate_slot() -> None:
    global _NEXT_REQUEST_AT
    with _REQUEST_LOCK:
        now = time.monotonic()
        wait = max(0.0, _NEXT_REQUEST_AT - now)
        if wait:
            time.sleep(wait)
        _NEXT_REQUEST_AT = time.monotonic() + MIN_REQUEST_INTERVAL_SECONDS


def _get_model() -> str:
    from common.model_config import MATCH_MODEL

    return os.environ.get("MATCH_MODEL") or MATCH_MODEL


def _do_api_call(client: Anthropic, model: str, prompt: str):
    """Anthropic API を呼ぶ。レートリミット/過負荷エラーは短期リトライする。"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            _wait_for_rate_slot()
            return client.messages.create(
                model=model,
                max_tokens=8000,
                temperature=0,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            err_str = str(e)
            if "529" in err_str or "overloaded" in err_str.lower():
                wait = 10 * (attempt + 1)
                print(f"[skill_judge] API過負荷(529) attempt={attempt + 1}/{max_retries} wait={wait}s")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Claude API 529 over max_retries")


def _classify_error_kind(e: Exception) -> str:
    """例外を SPEC §7.1 error_kind に分類する。"""
    if isinstance(e, (RateLimitError,)):
        return "transient"
    if isinstance(e, AuthenticationError):
        return "permanent_auth"
    if isinstance(e, BadRequestError):
        return "permanent_bad_request"
    if isinstance(e, NotFoundError):
        return "permanent_api"
    err_str = str(e)
    if "529" in err_str or "503" in err_str or "502" in err_str:
        return "transient"
    return "permanent_api"


def _judge_with_costguard(
    required_skills: list[str],
    prompt: str,
    target_id: str,
    est_in: int = 2000,
    est_out: int = 8000,
) -> dict:
    """cost_guard.allowed()/finalize() を経由してスキル判定を実行する。"""
    model = _get_model()
    decision: Decision = _cg_allowed(
        phase=PHASE,
        block_type=BLOCK_TYPE,
        target_id=target_id,
        est_in=est_in,
        est_out=est_out,
        model_hint=model,
        script="matching_v3_skill_judge",
    )

    if not decision.allowed:
        from common.exit_handler import ExitCode2

        if decision.exit_code == 2:
            raise ExitCode2(decision.reason, decision.detail)
        raise RuntimeError(f"[skill_judge] CostGuard blocked: reason={decision.reason}")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    client = Anthropic(api_key=api_key)
    actual_model = decision.model if decision.model else model

    error_kind = ""
    response = None
    try:
        response = _do_api_call(client, actual_model, prompt)
    except Exception as e:
        error_kind = _classify_error_kind(e)
        raise
    finally:
        in_tok = 0
        out_tok = 0
        if response is not None:
            usage = getattr(response, "usage", None)
            if usage:
                in_tok = getattr(usage, "input_tokens", 0)
                out_tok = getattr(usage, "output_tokens", 0)
        success = error_kind == ""
        _cg_finalize(
            decision,
            in_tokens=in_tok,
            out_tokens=out_tok,
            success=success,
            error_kind=error_kind if not success else "",
        )

    data = _parse_json_object(_extract_text(response))
    return _validate_result(required_skills, data)


def judge_skills(required_skills, engineer_skills, project_id: str = "") -> dict:
    """
    必須または尚可スキル群をエンジニアのスキルリストに照らして判定する。

    Args:
        required_skills: 判定したいスキル名リスト
        engineer_skills: エンジニアの保有スキルリスト
        project_id: 案件ID（dedup用 target_id、SPEC §5.4 では skill_judge で必須）

    Returns:
        {スキル名: {"result": "◯/×/△", "reason": "理由"}}
    """
    required_skills = _normalize_skill_list(required_skills)
    engineer_skills = _normalize_skill_list(engineer_skills)

    if not required_skills:
        return {}

    prompt = f"""
案件側スキル:
{json.dumps(required_skills, ensure_ascii=False)}

エンジニアのスキルリスト:
{json.dumps(engineer_skills, ensure_ascii=False)}

必ず次のJSONオブジェクトだけを返してください。説明文やMarkdownは不要です。
キーは案件側スキル名を完全にそのまま使ってください。
値は result と reason を持つオブジェクトにしてください。

例:
{{
  "Java": {{"result": "◯", "reason": "Java/Springの経験があり要件を満たす"}},
  "AWS": {{"result": "△", "reason": "クラウド経験はあるがAWS実務範囲は要確認"}}
}}
""".strip()

    return _judge_with_costguard(
        required_skills,
        prompt,
        target_id=project_id,
        est_in=len(prompt) // 4 + 500,
        est_out=8000,
    )
