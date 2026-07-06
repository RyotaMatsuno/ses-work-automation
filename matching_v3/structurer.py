from __future__ import annotations

import hashlib
import json
import logging
import os as _os
import re
import sys as _sys
from pathlib import Path
from typing import Any

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # matching_v3/ を最優先
_sys.path.insert(1, _os.path.join(_os.path.dirname(__file__), ".."))
from common.email_cleaner import clean_email_body
from common.ledger import can_spend as _ledger_can_spend
from common.ledger import record as _ledger_record
from common.normalizers import normalize_availability, normalize_rate_fields
from config import DEFAULT_STRUCTURER_MODEL, Config
from matching_cost_guard import CostGuard
from mail_pipeline.price_extractor import extract_price, resolve_final_price
from mail_pipeline.skill_extractor import extract_skills

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
FIXTURES_PATH = BASE_DIR / "tests" / "fixtures.json"
LOCATION_ALIASES_PATH = BASE_DIR / "location_aliases.json"
_LOCATION_ALIASES_CACHE: dict[str, list[str]] | None = None


def _load_location_aliases() -> dict[str, list[str]]:
    global _LOCATION_ALIASES_CACHE
    if _LOCATION_ALIASES_CACHE is None:
        with LOCATION_ALIASES_PATH.open("r", encoding="utf-8") as f:
            _LOCATION_ALIASES_CACHE = json.load(f)
    return _LOCATION_ALIASES_CACHE


def normalize_location_text(text: str | None) -> tuple[str | None, str | None]:
    """勤務地テキストを正規化し、(原文, canonical) を返す。"""
    if not text or not str(text).strip():
        return None, None
    raw = str(text).strip()
    lowered = raw.lower()
    for canonical, aliases in _load_location_aliases().items():
        for token in [canonical, *aliases]:
            if token.lower() in lowered:
                return raw, canonical
    return raw, None


def normalize_budget_from_text(budget_text: str | None) -> tuple[float | None, float | None]:
    """単価テキストから budget_min/max（万円）を推定する。"""
    if not budget_text:
        return None, None
    text = str(budget_text).strip()
    if not text:
        return None, None
    if "スキル見合い" in text or "スキルみ合い" in text:
        return None, None
    nums = [float(n) for n in re.findall(r"(\d+(?:\.\d+)?)", text.replace("，", ","))]
    if "前後" in text and len(nums) == 1:
        base = nums[0]
        return base - 3, base + 3
    if re.search(r"^[〜～]", text) and nums:
        return None, nums[-1]
    if re.search(r"[〜～]\s*$", text) and nums:
        return nums[0], None
    if len(nums) >= 2:
        return min(nums[0], nums[1]), max(nums[0], nums[1])
    if len(nums) == 1:
        return nums[0], nums[0]
    return None, None


def _apply_strict_schema(data: dict[str, Any]) -> dict[str, Any]:
    """v2スキーマを既存case_jsonフィールドへマージする。"""
    result = dict(data)
    if result.get("must_have_skills") and not result.get("required_skills"):
        result["required_skills"] = list(result["must_have_skills"])
    if result.get("nice_to_have_skills") and not result.get("optional_skills"):
        result["optional_skills"] = list(result["nice_to_have_skills"])
    if result.get("budget_min") is not None and result.get("price_min") is None:
        result["price_min"] = _coerce_price(result.get("budget_min"))
    if result.get("budget_max") is not None and result.get("price_max") is None:
        result["price_max"] = _coerce_price(result.get("budget_max"))
    text_min, text_max = normalize_budget_from_text(result.get("budget_text"))
    if result.get("price_min") is None and text_min is not None:
        result["price_min"] = text_min
    if result.get("price_max") is None and text_max is not None:
        result["price_max"] = text_max

    # BH: 「スキル見合い」「応相談」→ 推定単価レンジを補完（表示のみ、マッチング未反映）
    budget_text = str(result.get("budget_text") or "")
    _UNKNOWN_BUDGET_RE = (
        r"スキル見合|応相談|要相談|スキルみ合|単価要相談"
    )
    if result.get("price_min") is None and result.get("price_max") is None:
        import re as _re
        if not budget_text or _re.search(_UNKNOWN_BUDGET_RE, budget_text):
            try:
                from price_estimator import estimate_price as _estimate_price
                est = _estimate_price(result)
                result["budget_estimated"] = True
                result["budget_min_estimated"] = est.get("estimated_min")
                result["budget_max_estimated"] = est.get("estimated_max")
                result["budget_confidence_rank"] = est.get("confidence_rank", "low")
                result["budget_source"] = "estimated"
                result["budget_estimation_version"] = "v1_20260624"
            except Exception as _exc:
                logger.debug("price_estimator スキップ: %s", _exc)
        else:
            result["budget_source"] = "unknown"
    else:
        result["budget_source"] = "explicit"
        result["budget_estimated"] = False
    loc = result.get("location") or result.get("work_location")
    if loc:
        raw_loc, norm_loc = normalize_location_text(loc)
        result["work_location"] = raw_loc
        if norm_loc:
            result["location_normalized"] = norm_loc
    remote_type = str(result.get("remote_type") or "").lower()
    remote_map = {
        "full": "full",
        "remote": "full",
        "フルリモート": "full",
        "hybrid": "partial",
        "partial": "partial",
        "一部リモート": "partial",
        "none": "none",
        "onsite": "none",
        "出社": "none",
    }
    if remote_type in remote_map:
        result["remote_ok"] = remote_map[remote_type]
    if result.get("nationality_ok") is False:
        result["foreign_ok"] = False
    elif result.get("nationality_ok") is True:
        result["foreign_ok"] = True
    if result.get("age_limit") is not None and result.get("age_max") is None:
        try:
            result["age_max"] = int(result["age_limit"])
        except (TypeError, ValueError):
            pass
    field_conf = dict(result.get("field_confidence") or {})
    if not field_conf:
        field_conf = {
            "required_skills": 0.8 if result.get("required_skills") else 0.2,
            "price": 0.8 if result.get("price_min") is not None or result.get("price_max") is not None else 0.2,
            "location": 0.8 if result.get("work_location") else 0.2,
        }
        result["field_confidence"] = field_conf
    low_conf = [key for key, value in field_conf.items() if float(value) < 0.5]
    if low_conf:
        result["needs_review_fields"] = low_conf
    return result

SYSTEM_PROMPT = """あなたはSES（System Engineer Staffing）案件メールからJSON情報を抽出するアシスタントです。
メール本文を読み、指定されたJSONスキーマに従って情報を抽出してください。

ルール:
- 有効なJSONのみ出力する。説明文やMarkdownコードブロックを含めない
- 読み取れないフィールドはnullまたは空配列
- required_skills: 必須・必要と明記されたスキルのみ。具体的な技術・ツール名（Git, Slack, Backlog, MuleSoft, Salesforce, SQL, Terraform, LLM, AI活用, クラウド, Docker, Kubernetes等）および工程経験（要件定義経験, 設計経験, リーダー経験, PM経験, 開発経験, Webアプリ開発経験等）は必ずrequired_skillsに入れる
- optional_skills: 尚可・歓迎と明記されたスキル
- ambiguous_skills: ソフトスキル・非技術系・抽象的な工程表現のみ（例: "コミュニケーション能力", "主体性", "当事者意識", "営業経験", "インサイドセールス経験", "上流から一気通貫"等）。具体的な技術・工程経験・開発経験はambiguous_skillsに入れない
- price_min/max: 万円単位の数値（"〜60万"なら max=60.0, min=null）
- 単価が固定値の場合（例: "55万固定", "60万", "単価55万"）は price_min と price_max の両方に同じ値を入れる（55万固定 → min=55.0, max=55.0）
- 日付に年が明記されていない場合（例: "6/10", "6月10日"）は現在の年として解釈する。現在は2026年である。過去の年（2023年等）を使ってはならない
- extraction_confidence: 抽出の確信度（不明点が多い場合は低く）
- 推測禁止: 原文に無い情報はnull/空配列。単価・スキル・勤務地はメール本文からのみ抽出
- preferred_skills は optional_skills と同義（尚可スキル）
- location は work_location、remote_ratio は remote_ok（full/partial/none/unknown）
- 厳格スキーマ（いずれかで出力可）: must_have_skills / nice_to_have_skills / budget_min / budget_max / budget_text / location / location_normalized / remote_type / nationality_ok / age_limit / headcount
- 未抽出フィールドはnull（空文字禁止）。数値フィールドは数値型"""

MUST_NOT_PATTERNS: dict[str, list[str]] = {
    "外国籍不可": [r"外国籍[：:]*不可", r"外国籍NG", r"日本国籍のみ"],
    "年齢制限": [r"(\d{2})歳まで", r"(\d{2})代まで"],
    "出社必須": [r"出社必須", r"フル出社", r"リモート不可", r"常駐必須"],
    "弊社要員不可": [r"弊社.*不可", r"プロパー不可"],
}

RETRY_SYSTEM_PROMPT = """SES案件メールからJSONを抽出してください。有効なJSONのみ出力。
必須: required_skills, price_min/price_max(万円), work_location, role(案件名)。
読み取れない項目はnull。推測禁止。"""


def _empty_result(body: str = "", confidence: float = 0.0) -> dict[str, Any]:
    return {
        "role": None,
        "required_skills": [],
        "optional_skills": [],
        "ambiguous_skills": [],
        "price_min": None,
        "price_max": None,
        "start_date": None,
        "duration_months": None,
        "work_location": None,
        "remote_ok": "unknown",
        "interview_count": None,
        "foreign_ok": None,
        "required_phases": [],
        "settlement": None,
        "commercial_restrictions": None,
        "sole_proprietor_ok": None,
        "age_max": None,
        "night_shift": None,
        "interview_scheduled_at": None,
        "extraction_confidence": confidence,
        "raw_important_notes": body[:500] if body else None,
        "must_not": [],
    }


def is_recoverable(case_json: dict[str, Any]) -> bool:
    """ルールベース復旧後にマッチングへ進める最低条件。"""
    if case_json.get("required_skills"):
        return True
    if case_json.get("price_min") is not None or case_json.get("price_max") is not None:
        return True
    return float(case_json.get("extraction_confidence") or 0.0) >= 0.3


def rule_based_fallback(subject: str, body: str) -> dict[str, Any]:
    """件名+本文からルールベースで最低限フィールドを抽出する。"""
    return _rule_based_extract(subject, body)


def structure_case(
    case: dict[str, Any],
    body: str,
    cost_guard: CostGuard,
    config: Config | None = None,
) -> dict[str, Any]:
    subject = case.get("案件名") or case.get("subject") or ""
    return structure(body, cost_guard, config, notion_record=case, subject=subject)


def _notion_price(notion_record: dict[str, Any]) -> float | None:
    raw = notion_record.get("単価（万円）")
    if raw is None:
        raw = notion_record.get("単価")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _from_notion_direct(name: str, skills: list[str], price: float) -> dict[str, Any]:
    result = _empty_result(confidence=0.85)
    result["role"] = name
    result["required_skills"] = list(skills)
    result["price_min"] = price
    result["price_max"] = price
    result["structure_source"] = "notion_direct"
    return result


def _merge_case_json(base: dict[str, Any], supplement: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    used_supplement = False
    for key in ("required_skills", "optional_skills", "ambiguous_skills"):
        if not merged.get(key) and supplement.get(key):
            merged[key] = supplement[key]
            used_supplement = True
    for key in ("price_min", "price_max"):
        if merged.get(key) is None and supplement.get(key) is not None:
            merged[key] = supplement[key]
            used_supplement = True
    for key in ("role", "work_location", "start_date"):
        if not merged.get(key) and supplement.get(key):
            merged[key] = supplement[key]
            used_supplement = True
    conf = float(merged.get("extraction_confidence") or 0.0)
    sup_conf = float(supplement.get("extraction_confidence") or 0.0)
    merged["extraction_confidence"] = max(conf, sup_conf)
    if used_supplement and supplement.get("structure_source"):
        merged["structure_source"] = supplement["structure_source"]
    return merged


def _rule_based_extract(subject: str, body: str) -> dict[str, Any]:
    """LLMが失敗した場合のルールベース最小限抽出。"""
    skill_result = extract_skills(subject, body)
    required = list(skill_result.get("required", []))
    optional = list(skill_result.get("optional", []))
    price = resolve_final_price(None, subject, body)
    price_min = price
    price_max = price
    if price is None:
        price_info = extract_price(subject, body)
        if price_info.get("value") is not None and price_info.get("confidence") != "suspicious":
            value = float(price_info["value"])
            price_min = value
            price_max = value
    confidence = 0.5 if required and price_min is not None else (0.4 if required or price_min is not None else 0.0)
    result = _empty_result(body, confidence=confidence)
    result["required_skills"] = required
    result["optional_skills"] = optional
    result["structure_source"] = "rule_fallback"
    result["price_min"] = price_min
    result["price_max"] = price_max
    return result


def structure(
    body: str,
    cost_guard: CostGuard,
    config: Config | None = None,
    notion_record: dict[str, Any] | None = None,
    subject: str = "",
) -> dict[str, Any]:
    body = clean_email_body(body)
    subject = subject or (notion_record or {}).get("案件名", "") or ""
    rule_prefill = _rule_based_extract(subject, body)

    if notion_record:
        skills = notion_record.get("必要スキル") or []
        price = _notion_price(notion_record)
        name = notion_record.get("案件名", "")
        if skills and price is not None:
            result = _from_notion_direct(name, skills if isinstance(skills, list) else [skills], price)
            return _finalize_case_json(result, subject, body)
        if skills or price is not None:
            partial = _empty_result(confidence=0.6)
            partial["role"] = name
            if skills:
                partial["required_skills"] = skills if isinstance(skills, list) else [skills]
            if price is not None:
                partial["price_min"] = price
                partial["price_max"] = price
            partial["structure_source"] = "notion_partial"
            rule_prefill = _merge_case_json(partial, rule_prefill)
            if is_recoverable(rule_prefill) and (
                rule_prefill.get("required_skills") and rule_prefill.get("price_min") is not None
            ):
                return _finalize_case_json(rule_prefill, subject, body)

    cfg = config or Config()
    prompt_text = _build_prompt(_truncate_body(body))
    est_input_tokens = len(prompt_text) // 4 + 200
    est_output_tokens = 300
    if not _ledger_can_spend(est_input_tokens, est_output_tokens, DEFAULT_STRUCTURER_MODEL):
        logger.warning("Global cost limit reached, skipping")
        raise RuntimeError("global cost limit reached")
    if not cost_guard.can_call(
        est_input_tokens,
        est_output_tokens,
        target_id=hashlib.sha256(f"{subject}\n{body[:500]}".encode()).hexdigest()[:32],
    ):
        logger.warning("Cost limit reached, skipping")
        raise RuntimeError("cost limit reached")

    model = cost_guard.get_model()
    try:
        if model.startswith("gpt-") or model.startswith("o"):
            response = _call_openai(prompt_text, model, cfg)
        else:
            response = _call_anthropic(prompt_text, model, cfg)
    except Exception:
        cost_guard.abort_pending()
        raise
    usage = getattr(response, "usage", None)
    input_tokens = int(
        getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None) or est_input_tokens
    )
    output_tokens = int(
        getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None) or est_output_tokens
    )
    cost_guard.record_cost(input_tokens, output_tokens, model)
    _ledger_record(input_tokens, output_tokens, model, "matching_v3")
    text = _response_text(response)
    llm_result = _parse_json_or_fallback(text, subject, body, postprocess=False)
    merged = _merge_case_json(llm_result, rule_prefill)
    if not is_recoverable(merged):
        merged = _merge_case_json(merged, _rule_based_extract(subject, body))

    merged = _postprocess_case_json(merged, subject, body)
    completeness = _compute_required_completeness(merged, subject)
    if completeness < 0.6:
        retried = _retry_structure(body, subject, cost_guard, cfg)
        if retried:
            merged = _merge_case_json(merged, retried)
            merged = _postprocess_case_json(merged, subject, body)
            merged["extraction_retried"] = True
            completeness = _compute_required_completeness(merged, subject)
    if completeness < 0.6:
        merged["quality_flag"] = "NEEDS_REVIEW"
    merged["field_completeness"] = completeness
    return merged


def _truncate_body(body: str) -> str:
    if len(body) > 3000:
        return body[:2000] + body[-1000:]
    return body


def _build_prompt(body: str) -> str:
    examples = _load_examples()
    lines = [
        "以下のFew-shot例を参考に、最後のメール本文をJSON構造化してください。",
        "",
    ]
    for index, item in enumerate(examples, start=1):
        lines.extend(
            [
                f"例{index} 入力:",
                item["body"],
                f"例{index} 出力:",
                json.dumps(item["expected"], ensure_ascii=False),
                "",
            ]
        )
    lines.extend(["対象メール本文:", body])
    return "\n".join(lines)


def _load_examples() -> list[dict[str, Any]]:
    with FIXTURES_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("case_examples", [])[:5]


def _split_composite_skills(skills: list[str]) -> list[str]:
    out: list[str] = []
    for skill in skills:
        for part in re.split(r"[/／、,]", str(skill)):
            part = part.strip()
            if part:
                out.append(part)
    return out


def _coerce_price(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        m = re.search(r"(\d+(?:\.\d+)?)", value.replace("万", ""))
        if not m:
            return None
        value = m.group(1)
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    if price >= 1000:
        price = price / 10000
    return price if price > 0 else None


def _normalize_skills_list(skills: list[str]) -> list[str]:
    try:
        from matcher import SkillNormalizer

        normalizer = SkillNormalizer(BASE_DIR / "skill_aliases.json")
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in _split_composite_skills(skills):
            canon = normalizer.normalize_hard(raw) or raw.strip()
            if canon and canon not in seen:
                seen.add(canon)
                normalized.append(canon)
        return normalized
    except Exception:
        return _split_composite_skills(skills)


def _compute_extraction_confidence(data: dict[str, Any]) -> float:
    fields = 0
    filled = 0
    if data.get("required_skills"):
        filled += 1
    fields += 1
    if data.get("price_min") is not None or data.get("price_max") is not None:
        filled += 1
    fields += 1
    if data.get("work_location"):
        filled += 1
    fields += 1
    if data.get("remote_ok") not in (None, "", "unknown"):
        filled += 1
    fields += 1
    return round(filled / fields, 2) if fields else 0.0


def _extract_must_not(body: str) -> dict[str, Any]:
    found: list[str] = []
    age_max: int | None = None
    for label, patterns in MUST_NOT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, body)
            if not match:
                continue
            if label not in found:
                found.append(label)
            if label == "年齢制限":
                if match.lastindex and match.group(1).isdigit():
                    value = int(match.group(1))
                    age_max = value if value > 12 else value * 10 + 9
                else:
                    gen = re.search(r"(\d{2})代まで", match.group(0))
                    if gen:
                        age_max = int(gen.group(1)) * 10 + 9
            break
    return {"must_not": found, "age_max": age_max}


def _compute_required_completeness(data: dict[str, Any], subject: str = "") -> float:
    filled = 0
    if data.get("required_skills"):
        filled += 1
    if data.get("price_min") is not None or data.get("price_max") is not None:
        filled += 1
    if data.get("work_location"):
        filled += 1
    if data.get("role") or subject.strip():
        filled += 1
    return round(filled / 4, 2)


def _finalize_case_json(data: dict[str, Any], subject: str, body: str) -> dict[str, Any]:
    result = _postprocess_case_json(data, subject, body)
    completeness = _compute_required_completeness(result, subject)
    if completeness < 0.6:
        result["quality_flag"] = "NEEDS_REVIEW"
    result["field_completeness"] = completeness
    return result


def _retry_structure(
    body: str,
    subject: str,
    cost_guard: CostGuard,
    config: Config,
) -> dict[str, Any] | None:
    prompt = f"件名: {subject}\n\n本文:\n{_truncate_body(body)}"
    est_input_tokens = len(prompt) // 4 + 100
    est_output_tokens = 200
    if not cost_guard.can_call(
        est_input_tokens,
        est_output_tokens,
        target_id=hashlib.sha256(f"{subject}\n{body[:500]}".encode()).hexdigest()[:32],
    ):
        logger.warning("Cost limit reached, skipping extraction retry")
        return None
    model = cost_guard.get_model()
    try:
        if model.startswith("gpt-") or model.startswith("o"):
            response = _call_openai_retry(prompt, model, config)
        else:
            response = _call_anthropic_retry(prompt, model, config)
    except Exception as exc:
        cost_guard.abort_pending()
        logger.warning("Extraction retry failed: %s", exc)
        return None
    usage = getattr(response, "usage", None)
    input_tokens = int(
        getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None) or est_input_tokens
    )
    output_tokens = int(
        getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None) or est_output_tokens
    )
    cost_guard.record_cost(input_tokens, output_tokens, model)
    _ledger_record(input_tokens, output_tokens, model, "matching_v3_retry")
    text = _response_text(response)
    return _parse_json_or_fallback(text, subject, body, postprocess=False)


def _call_anthropic_retry(prompt_text: str, model: str, config: Config):
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package is required") from exc
    api_key = config.anthropic_api_key
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is required")
    client = anthropic.Anthropic(api_key=api_key)
    return client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        system=RETRY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt_text}],
    )


def _call_openai_retry(prompt_text: str, model: str, config: Config):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is required") from exc
    api_key = config.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    client = OpenAI(api_key=api_key)
    return client.chat.completions.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": RETRY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
    )


def _postprocess_case_json(data: dict[str, Any], subject: str = "", body: str = "") -> dict[str, Any]:
    result = _apply_strict_schema(dict(data))
    req = result.get("required_skills") or []
    opt = result.get("optional_skills") or result.get("preferred_skills") or []
    result["required_skills"] = _normalize_skills_list(list(req))
    result["optional_skills"] = _normalize_skills_list(list(opt))
    pmin, pmax, rate_warnings = normalize_rate_fields(
        result.get("price_min") or result.get("rate_min"),
        result.get("price_max") or result.get("rate_max"),
    )
    result["price_min"] = pmin
    result["price_max"] = pmax
    for warning in rate_warnings:
        logger.warning(warning)
    if result.get("start_date"):
        normalized_start = normalize_availability(result.get("start_date"))
        if normalized_start:
            result["start_date"] = normalized_start
    must_not_info = _extract_must_not(body)
    result["must_not"] = must_not_info.get("must_not") or result.get("must_not") or []
    if must_not_info.get("age_max") is not None and result.get("age_max") is None:
        result["age_max"] = must_not_info["age_max"]
    if not result["required_skills"] and subject:
        fallback = _rule_based_extract(subject, body)
        result["required_skills"] = fallback.get("required_skills") or []
        if result.get("price_min") is None:
            result["price_min"] = fallback.get("price_min")
        if result.get("price_max") is None:
            result["price_max"] = fallback.get("price_max")
    conf = _compute_extraction_confidence(result)
    result["extraction_confidence"] = conf
    if conf < 0.3:
        result["structure_failed"] = True
        try:
            from common.failure_collector import collect_failure

            collect_failure(
                "extraction_fail",
                {"subject": subject, "required_skills": result.get("required_skills", [])},
                f"confidence={conf}",
            )
        except Exception:
            pass
    return result


def _call_anthropic(prompt_text: str, model: str, config: Config):
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package is required") from exc
    api_key = config.anthropic_api_key
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is required")
    client = anthropic.Anthropic(api_key=api_key)
    return client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt_text}],
    )


def _call_openai(prompt_text: str, model: str, config: Config):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is required: pip install openai") from exc
    api_key = config.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
    )
    if getattr(resp.choices[0], "finish_reason", None) == "length":
        logger.warning("OpenAI response truncated by max_tokens")
    return resp


def _response_text(response: Any) -> str:
    # OpenAI ChatCompletion
    if hasattr(response, "choices"):
        return response.choices[0].message.content or ""
    # Anthropic Messages
    content = getattr(response, "content", [])
    parts: list[str] = []
    for item in content:
        text = getattr(item, "text", None)
        if text is None and isinstance(item, dict):
            text = item.get("text")
        if text:
            parts.append(text)
    return "".join(parts)


def _parse_json_or_fallback(
    text: str,
    subject: str = "",
    body: str = "",
    *,
    postprocess: bool = True,
) -> dict[str, Any]:
    # markdown fence stripping (LLMが```json...```で返した場合)
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```\s*$", "", t).strip()
    if not t:
        logger.warning("Structurer: empty response text")
        stripped = ""
    else:
        stripped = t

    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return _postprocess_case_json(data, subject, body) if postprocess else data
    except json.JSONDecodeError:
        logger.warning("Structurer JSON parse failed (first 200 chars): %s", stripped[:200])

    m = re.search(r"\{.*\}", stripped, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group())
            if isinstance(data, dict):
                return _postprocess_case_json(data, subject, body) if postprocess else data
        except json.JSONDecodeError:
            pass

    logger.warning("Structurer: falling back to rule-based extraction")
    return _rule_based_extract(subject, body or stripped)
