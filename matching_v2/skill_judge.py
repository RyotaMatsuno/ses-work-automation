# -*- coding: utf-8 -*-
"""
Claude APIによるスキル判定モジュール。

judge_skills(required_skills, engineer_skills) は1リクエストで複数スキルを判定し、
{スキル名: {"result": "◯/×/△", "reason": "理由"}} を返す。
"""

import json
import os
import re
import sys
import time
from threading import Lock

from anthropic import Anthropic
from anthropic import NotFoundError
from anthropic import RateLimitError

BASE_DIR = os.path.dirname(__file__)
SES_WORK_DIR = os.path.dirname(BASE_DIR)
if SES_WORK_DIR not in sys.path:
    sys.path.insert(0, SES_WORK_DIR)

from usage_tracker.cost_logger import log_cost


MODEL_NAME = "claude-haiku-4-5-20251001"
VALID_RESULTS = {"◯", "×", "△"}
SYSTEM_PROMPT = """
あなたはSES案件のスキルマッチング担当です。
案件側のスキル要件ごとに、エンジニアのスキルリストで満たせるか判定してください。

判定ルール:
- "◯": 表記ゆれ、関連フレームワーク、明確な実務経験から満たすと判断できる
- "△": 基礎のみ、部分経験、近いが実務確認が必要
- "×": 経験が見当たらない、または要件を満たす根拠がない

必ずJSONオブジェクトだけを返してください。説明文やMarkdownは不要です。
値は result と reason を持つオブジェクトにしてください。
""".strip()
_SELECTED_MODEL = None
_REQUEST_LOCK = Lock()
_NEXT_REQUEST_AT = 0.0
MIN_REQUEST_INTERVAL_SECONDS = float(
    os.environ.get("ANTHROPIC_MIN_INTERVAL_SECONDS", "1.4")
)
RATE_LIMIT_RETRY_SECONDS = [70, 70, 70]


def _normalize_skill_list(skills):
    if not skills:
        return []
    return [str(skill).strip() for skill in skills if str(skill).strip()]


def _extract_text(response):
    texts = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            texts.append(text)
    return "\n".join(texts).strip()


def _parse_json_object(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _validate_result(required_skills, data):
    normalized = {}
    for skill in required_skills:
        item = data.get(skill, {})
        result = str(item.get("result", "×")).strip()
        reason = str(item.get("reason", "判定結果が不正です")).strip()
        if result not in VALID_RESULTS:
            result = "×"
            reason = "判定結果が◯/×/△以外だったため除外扱いにしました"
        normalized[skill] = {
            "result": result,
            "reason": reason,
        }
    return normalized


def _validate_batch_result(skills_to_judge, engineers, data):
    normalized = {}
    for engineer in engineers:
        engineer_name = engineer["name"]
        engineer_data = data.get(engineer_name, {})
        normalized[engineer_name] = _validate_result(skills_to_judge, engineer_data)
    return normalized


def _select_fallback_model(client):
    model_list = client.models.list(limit=20)
    sonnet_models = [
        model.id for model in model_list.data
        if "sonnet" in model.id
    ]
    if sonnet_models:
        return sonnet_models[0]
    if model_list.data:
        return model_list.data[0].id
    raise RuntimeError("Anthropic APIで利用可能なモデルが見つかりません")


def _wait_for_rate_slot():
    global _NEXT_REQUEST_AT

    with _REQUEST_LOCK:
        now = time.monotonic()
        wait_seconds = max(0.0, _NEXT_REQUEST_AT - now)
        if wait_seconds:
            time.sleep(wait_seconds)
        _NEXT_REQUEST_AT = time.monotonic() + MIN_REQUEST_INTERVAL_SECONDS


def _messages_create(client, model_name, prompt):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            _wait_for_rate_slot()
            return client.messages.create(
                model=model_name,
                max_tokens=4000,
                temperature=0,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
        except Exception as e:
            err_str = str(e)
            if "529" in err_str or "overloaded" in err_str.lower():
                wait = 10 * (attempt + 1)
                print(
                    f"[skill_judge] API過負荷(529) "
                    f"attempt={attempt + 1}/{max_retries} wait={wait}s"
                )
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Claude API 529 over max_retries")


def _create_message(client, prompt):
    global _SELECTED_MODEL

    model_name = os.environ.get("ANTHROPIC_MODEL") or _SELECTED_MODEL or MODEL_NAME
    try:
        response = _messages_create(client, model_name, prompt)
        _SELECTED_MODEL = model_name
        _log_response_cost(response, model_name)
        return response
    except NotFoundError:
        if model_name != MODEL_NAME:
            raise
        fallback_model = _select_fallback_model(client)
        response = _messages_create(client, fallback_model, prompt)
        _SELECTED_MODEL = fallback_model
        _log_response_cost(response, fallback_model)
        return response
    except RateLimitError:
        for wait_seconds in RATE_LIMIT_RETRY_SECONDS:
            time.sleep(wait_seconds)
            try:
                response = _messages_create(client, model_name, prompt)
                _SELECTED_MODEL = model_name
                _log_response_cost(response, model_name)
                return response
            except RateLimitError:
                continue
        raise


def _log_response_cost(response, model_name):
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    log_cost(
        script_name="matching_v2",
        model=getattr(response, "model", None) or model_name,
        input_tokens=getattr(usage, "input_tokens", 0),
        output_tokens=getattr(usage, "output_tokens", 0),
        cached_tokens=getattr(usage, "cache_read_input_tokens", 0),
    )


def judge_skills(required_skills, engineer_skills):
    """
    必須または尚可スキル群を、エンジニアのスキルリストに照らして判定する。

    Args:
        required_skills (list): 判定したいスキル名リスト
        engineer_skills (list): エンジニアの保有スキルリスト

    Returns:
        dict: {スキル名: {"result": "◯/×/△", "reason": "理由"}}
    """
    required_skills = _normalize_skill_list(required_skills)
    engineer_skills = _normalize_skill_list(engineer_skills)

    if not required_skills:
        return {}

    api_key = os.environ["ANTHROPIC_API_KEY"]
    client = Anthropic(api_key=api_key)

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

    response = _create_message(client, prompt)
    data = _parse_json_object(_extract_text(response))
    return _validate_result(required_skills, data)


def judge_skills_batch(required_skills, optional_skills, engineers):
    """
    案件1件の必須・尚可スキルを、全エンジニア分まとめて判定する。

    Args:
        required_skills (list): 必須スキル名リスト
        optional_skills (list): 尚可スキル名リスト
        engineers (list): dict{name, skills} のリスト

    Returns:
        dict: {エンジニア名: {スキル名: {"result": "◯/×/△", "reason": "理由"}}}
    """
    required_skills = _normalize_skill_list(required_skills)
    optional_skills = _normalize_skill_list(optional_skills)
    skills_to_judge = required_skills + optional_skills
    normalized_engineers = [
        {
            "name": str(engineer.get("name", "")).strip(),
            "skills": _normalize_skill_list(engineer.get("skills", [])),
            "skill_text": str(engineer.get("skill_text", "")).strip(),
        }
        for engineer in engineers
        if str(engineer.get("name", "")).strip()
    ]

    if not skills_to_judge or not normalized_engineers:
        return {}

    api_key = os.environ["ANTHROPIC_API_KEY"]
    client = Anthropic(api_key=api_key)


    # skill_textがあればそれを優先してプロンプトに渡す
    engineers_for_prompt = []
    for eng in normalized_engineers:
        skill_text = eng.get("skill_text", "")
        if skill_text:
            engineers_for_prompt.append({
                "name": eng["name"],
                "skill_description": skill_text,
            })
        else:
            engineers_for_prompt.append({
                "name": eng["name"],
                "skills": eng["skills"],
            })
    prompt = f"""
案件側スキル:
{json.dumps(skills_to_judge, ensure_ascii=False)}

エンジニア一覧:
{json.dumps(engineers_for_prompt, ensure_ascii=False)}

次のJSON構造で返してください。
最上位キーはエンジニア名を完全にそのまま使ってください。
各エンジニア配下のキーは案件側スキル名を完全にそのまま使ってください。

例:
{{
  "田中太郎": {{
    "Java": {{"result": "◯", "reason": "Java/Springの経験があり要件を満たす"}},
    "AWS": {{"result": "△", "reason": "クラウド経験はあるがAWS実務範囲は要確認"}}
  }},
  "佐藤花子": {{
    "Java": {{"result": "×", "reason": "Java経験が見当たらない"}},
    "AWS": {{"result": "◯", "reason": "AWS実務経験がある"}}
  }}
}}
""".strip()

    response = _create_message(client, prompt)
    data = _parse_json_object(_extract_text(response))
    return _validate_batch_result(skills_to_judge, normalized_engineers, data)
