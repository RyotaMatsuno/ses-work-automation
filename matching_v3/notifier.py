from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from config import Config
from matcher import (
    SkillNormalizer,
    _engineer_has_canonical,
    _engineer_staleness_source,
    calc_gross_profit,
    engineer_unit_price_man,
    is_engineer_fresh,
)

logger = logging.getLogger(__name__)
JST = timezone(timedelta(hours=9))
_BASE_DIR = Path(__file__).resolve().parent
_LEADER_KEYWORDS = ("リーダー", "テックリード", "PM", "PL", "リード")
_UPSTREAM_KEYWORDS = ("要件定義", "基本設計", "上流", "上流工程")
_PARALLEL_STATUS_LABELS = {
    "面談調整中": "面談調整中",
    "面談予定": "面談予定",
    "結果待ち": "結果待ち",
    "オファー中": "オファー中",
}


@dataclass
class QueuedMessage:
    user_key: str
    user_id: str
    text: str
    immediate: bool = False


class Notifier:
    PUSH_LIMIT_PER_DAY = 6  # 平日のみ稼働: 22日×6=132通/月 < 200通上限
    PUSH_URL = "https://api.line.me/v2/bot/message/push"

    def __init__(self, config: Config | None = None, session: requests.Session | None = None) -> None:
        self.config = config or Config()
        self.session = session or requests.Session()
        self.queue: list[QueuedMessage] = []
        self.sent_count = 0

    def enqueue(
        self,
        case: dict[str, Any],
        engineer: dict[str, Any],
        verdict: str,
        reasons: list[str],
        *,
        score: float | None = None,
        priority: bool = False,
    ) -> None:
        case_user = self.get_user_by_notion_assignee(case.get("担当者"))
        eng_user = self.get_user_by_notion_assignee(engineer.get("担当者"))
        immediate = bool(case.get("interview_scheduled_at") or case.get("case_json", {}).get("interview_scheduled_at"))

        if case_user and eng_user and case_user["key"] == eng_user["key"]:
            self._enqueue(
                case_user,
                self._build_msg(case, engineer, verdict, reasons, score=score, priority=priority),
                immediate,
            )
        elif case_user and eng_user:
            case_name = case.get("案件名", "")
            self._enqueue(
                case_user,
                f"【{verdict}】{case_name} - {eng_user['key']}に意向確認を依頼済み",
                immediate,
            )
            self._enqueue(
                eng_user,
                f"【意向確認依頼】{case_name}　担当: {case_user['key']}",
                immediate,
            )

    def flush(self, dry_run: bool = False) -> None:
        by_user: dict[tuple[str, str], list[str]] = {}
        for item in self.queue:
            key = (item.user_key, item.user_id)
            if item.immediate:
                self._push(item.user_id, item.text, dry_run=dry_run)
            else:
                by_user.setdefault(key, []).append(item.text)

        for (_, user_id), messages in by_user.items():
            self._push(user_id, "\n\n".join(messages), dry_run=dry_run)
        self.queue.clear()

    def get_user_by_notion_assignee(self, assignee: str | None) -> dict[str, Any] | None:
        if not assignee:
            return None
        for key, user in self.config.users.items():
            if user.get("notion_assignee") == assignee:
                data = dict(user)
                data["key"] = key
                return data
        return None

    def _enqueue(self, user: dict[str, Any], text: str, immediate: bool) -> None:
        user_id = user.get("line_user_id")
        if not user_id:
            return
        self.queue.append(QueuedMessage(user["key"], user_id, text, immediate))

    def _push(self, user_id: str, text: str, dry_run: bool = False) -> None:
        if self.sent_count >= self.PUSH_LIMIT_PER_DAY:
            logger.warning("LINE push daily limit reached")
            return
        if dry_run:
            self.sent_count += 1
            return
        token = self.config.line_channel_access_token
        if not token:
            raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is required")
        response = self.session.post(
            self.PUSH_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"to": user_id, "messages": [{"type": "text", "text": text}]},
            timeout=30,
        )
        response.raise_for_status()
        self.sent_count += 1

    @staticmethod
    def _build_msg(
        case: dict[str, Any],
        engineer: dict[str, Any],
        verdict: str,
        reasons: list[str],
        *,
        score: float | None = None,
        priority: bool = False,
    ) -> str:
        summary = build_proposal_summary(case, engineer, verdict, reasons)
        prefix = "【優先】" if priority else ""
        text = summary["internal_text"]
        if score is not None:
            text = f"{prefix}{text}\nマッチスコア: {score:.2f}"
        elif prefix:
            text = f"{prefix}{text}"
        return text


def build_proposal_summary(
    case: dict[str, Any],
    engineer: dict[str, Any],
    verdict: str,
    reasons: list[str],
    *,
    normalizer: SkillNormalizer | None = None,
) -> dict[str, Any]:
    """提案文サマリー（案件向け・内部向け）を生成する。"""
    case_json = case.get("case_json") or case
    norm = normalizer or SkillNormalizer(_BASE_DIR / "skill_aliases.json")
    skill_matches = _analyze_skill_matches(case_json, engineer, norm)
    price_info = _price_alignment(case_json, engineer, reasons)
    start_info = _start_date_alignment(case_json, engineer)
    parallel_text = _format_parallel_status(engineer)
    concerns = _collect_concerns(case_json, engineer, skill_matches, reasons)
    appeal = _build_appeal_text(case_json, engineer, skill_matches, price_info)

    skill_section = _format_skill_section(skill_matches)
    price_line = _format_price_line(price_info)
    start_line = _format_start_line(start_info)
    concern_lines = [f"・{item}" for item in concerns]

    initial = _initial(engineer.get("名前", ""))
    case_name = case.get("案件名", case_json.get("role", ""))

    client_lines = [
        f"【ご提案】{case_name}",
        f"{initial}様は{appeal}かと存じます。",
        skill_section,
        price_line,
        start_line,
        f"並行状況: {parallel_text}",
        "ご検討いただけますと幸いです。何卒よろしくお願いいたします。",
    ]

    internal_header = (
        f"【{verdict}】{case_name}"
        if verdict in ("MATCH", "REVIEW", "PARTIAL_MATCH")
        else f"【要確認】{case_name}"
    )
    internal_lines = [
        internal_header,
        f"候補: {initial}",
        f"アピール: {appeal}",
        skill_section,
        price_line,
        start_line,
        f"並行: {parallel_text}",
    ]
    if concern_lines:
        internal_lines.extend(["懸念:", *concern_lines])
    if reasons:
        internal_lines.extend(["判定根拠:", *[f"・{reason}" for reason in reasons]])

    return {
        "appeal": appeal,
        "client_text": "\n".join(line for line in client_lines if line),
        "internal_text": "\n".join(line for line in internal_lines if line),
        "skill_matches": skill_matches,
        "price_info": price_info,
        "start_info": start_info,
        "parallel_text": parallel_text,
        "concerns": concerns,
    }


def _analyze_skill_matches(
    case_json: dict[str, Any],
    engineer: dict[str, Any],
    normalizer: SkillNormalizer,
) -> dict[str, list[str]]:
    eng_skills_raw = [str(skill) for skill in (engineer.get("スキル") or [])]
    eng_canonical = _engineer_canonical_set(eng_skills_raw, normalizer)
    grouped: dict[str, list[str]] = {"exact": [], "alias": [], "soft_alias": [], "optional_miss": []}

    for skill in case_json.get("required_skills") or []:
        match_type = _classify_skill_match(skill, eng_skills_raw, eng_canonical, normalizer, optional=False)
        if match_type:
            grouped[match_type].append(skill)

    for skill in case_json.get("optional_skills") or []:
        match_type = _classify_skill_match(skill, eng_skills_raw, eng_canonical, normalizer, optional=True)
        if match_type:
            grouped[match_type].append(skill)
        else:
            grouped["optional_miss"].append(skill)

    return grouped


def _engineer_canonical_set(eng_skills_raw: list[str], normalizer: SkillNormalizer) -> set[str]:
    eng_canonical: set[str] = set()
    for skill in eng_skills_raw:
        normalized = normalizer.normalize_hard(skill)
        eng_canonical.add(normalized if normalized else skill)
        soft = normalizer.normalize_soft(skill)
        if soft:
            eng_canonical.add(soft)
    return eng_canonical


def _classify_skill_match(
    req: str,
    eng_skills_raw: list[str],
    eng_canonical: set[str],
    normalizer: SkillNormalizer,
    *,
    optional: bool,
) -> str | None:
    canonical = normalizer.normalize_hard(req)
    target = canonical or req.strip()
    req_soft = normalizer.normalize_soft(req)

    if canonical and _engineer_has_canonical(canonical, eng_canonical, normalizer.parent_skills):
        return _match_type_for_target(req, target, eng_skills_raw, normalizer)

    if req_soft and req_soft in eng_canonical:
        return "soft_alias"

    if optional:
        for eng_skill in eng_skills_raw:
            eng_soft = normalizer.normalize_soft(eng_skill)
            if eng_soft and (eng_soft == target or (req_soft and eng_soft == req_soft)):
                return "soft_alias"
    return None


def _match_type_for_target(
    req: str,
    target: str,
    eng_skills_raw: list[str],
    normalizer: SkillNormalizer,
) -> str:
    req_key = normalizer._skill_key(req)
    saw_alias = False
    saw_soft = False
    for eng_skill in eng_skills_raw:
        eng_key = normalizer._skill_key(eng_skill)
        eng_hard = normalizer.normalize_hard(eng_skill)
        eng_soft = normalizer.normalize_soft(eng_skill)
        if eng_key == req_key or eng_skill.strip() == req.strip():
            return "exact"
        if eng_hard == target:
            if eng_key in normalizer.hard:
                saw_alias = True
            else:
                return "exact"
        if eng_soft == target or eng_soft == normalizer.normalize_soft(req):
            saw_soft = True
    if saw_alias:
        return "alias"
    if saw_soft:
        return "soft_alias"
    return "exact"


def _build_appeal_text(
    case_json: dict[str, Any],
    engineer: dict[str, Any],
    skill_matches: dict[str, list[str]],
    price_info: dict[str, Any],
) -> str:
    required = case_json.get("required_skills") or []
    optional = case_json.get("optional_skills") or []
    req_matched = [
        skill
        for skill in required
        if skill in skill_matches["exact"] or skill in skill_matches["alias"] or skill in skill_matches["soft_alias"]
    ]
    opt_matched = [
        skill
        for skill in optional
        if skill in skill_matches["exact"] or skill in skill_matches["alias"] or skill in skill_matches["soft_alias"]
    ]
    required_all = bool(required) and len(req_matched) == len(required)
    optional_all = bool(optional) and len(opt_matched) == len(optional)

    if required_all and optional_all:
        return "必須・尚可ともにマッチ度高い人員"
    if required_all and _has_leader_experience(engineer, case_json):
        return "必須全て満たしており、リーダー経験あり"
    if required_all and _has_upstream_experience(engineer, case_json):
        return "必須全て満たしており、上流工程経験あり"
    if required_all and _is_price_advantage_young(engineer, price_info):
        return "必須全て満たしており、単価面で優位な若手"
    if required_all and optional and len(opt_matched) / len(optional) >= 0.5:
        items = "・".join(opt_matched[:3])
        return f"必須全て満たしており、尚可も{items}経験あり"
    if required_all:
        return "必須スキル全て満たし即稼働可能"
    return "マッチ度高い人員"


def _has_leader_experience(engineer: dict[str, Any], case_json: dict[str, Any]) -> bool:
    texts = _skill_texts(engineer, case_json)
    return any(any(keyword in text for keyword in _LEADER_KEYWORDS) for text in texts)


def _has_upstream_experience(engineer: dict[str, Any], case_json: dict[str, Any]) -> bool:
    texts = _skill_texts(engineer, case_json)
    phases = [str(phase) for phase in (case_json.get("required_phases") or [])]
    texts.extend(phases)
    return any(any(keyword in text for keyword in _UPSTREAM_KEYWORDS) for text in texts)


def _skill_texts(engineer: dict[str, Any], case_json: dict[str, Any]) -> list[str]:
    return [str(skill) for skill in (engineer.get("スキル") or [])] + [
        str(skill) for skill in (case_json.get("required_skills") or [])
    ]


def _is_price_advantage_young(engineer: dict[str, Any], price_info: dict[str, Any]) -> bool:
    years = engineer.get("経験年数")
    try:
        years_value = float(years)
    except (TypeError, ValueError):
        years_value = None
    eng_price = price_info.get("engineer_price")
    case_max = price_info.get("case_max")
    if years_value is None or eng_price is None or case_max is None:
        return False
    return years_value <= 4 and eng_price <= case_max * 0.85


def _price_alignment(case_json: dict[str, Any], engineer: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    case_min = _to_float(case_json.get("price_min"))
    case_max = _to_float(case_json.get("price_max"))
    eng_price = engineer_unit_price_man(engineer)
    estimated = any("単価推定" in reason for reason in reasons)
    gross = None
    if case_max is not None and eng_price is not None:
        gross = round(calc_gross_profit(case_max, eng_price), 1)
    aligned = gross is not None and gross >= 0
    return {
        "case_min": case_min,
        "case_max": case_max,
        "engineer_price": eng_price,
        "gross_profit": gross,
        "estimated": estimated,
        "aligned": aligned,
    }


def _start_date_alignment(case_json: dict[str, Any], engineer: dict[str, Any]) -> dict[str, Any]:
    case_start = _parse_date(case_json.get("start_date"))
    eng_start = _parse_date(engineer.get("稼働開始"))
    eng_status = str(engineer.get("稼働状況") or "").strip()
    aligned = True
    note = ""
    if case_start and eng_start and eng_start > case_start:
        aligned = False
        note = f"案件開始{case_start.isoformat()}に対し稼働開始{eng_start.isoformat()}が遅い"
    elif case_start and not eng_start and eng_status and "即" not in eng_status and "可" not in eng_status:
        aligned = False
        note = f"案件開始{case_start.isoformat()}に対し稼働時期要確認（{eng_status}）"
    return {
        "case_start": case_start.isoformat() if case_start else None,
        "engineer_start": eng_start.isoformat() if eng_start else eng_status or None,
        "aligned": aligned,
        "note": note,
    }


def _collect_concerns(
    case_json: dict[str, Any],
    engineer: dict[str, Any],
    skill_matches: dict[str, list[str]],
    reasons: list[str],
) -> list[str]:
    concerns: list[str] = []
    soft_only_required = [
        skill
        for skill in (case_json.get("required_skills") or [])
        if skill in skill_matches["soft_alias"]
        and skill not in skill_matches["exact"]
        and skill not in skill_matches["alias"]
    ]
    if soft_only_required:
        concerns.append(f"soft_alias一致のみ: {', '.join(soft_only_required)}")

    if not is_engineer_fresh(engineer):
        _, days_old = _engineer_staleness_source(engineer)
        if days_old >= 0:
            concerns.append(f"鮮度警告: {days_old}日前更新")
        else:
            concerns.append("鮮度警告: 最終更新日不明")

    parallel_text = _format_parallel_status(engineer)
    if parallel_text not in ("なし", ""):
        concerns.append(f"並行状況: {parallel_text}")

    for reason in reasons:
        if reason.startswith("曖昧スキルあり"):
            concerns.append(reason)
        if reason.startswith("構造化精度低"):
            concerns.append(reason)

    start_info = _start_date_alignment(case_json, engineer)
    if start_info.get("note"):
        concerns.append(start_info["note"])

    return concerns


def _format_skill_section(skill_matches: dict[str, list[str]]) -> str:
    lines = []
    for label, key in (("完全一致", "exact"), ("alias一致", "alias"), ("soft_alias一致", "soft_alias")):
        skills = skill_matches.get(key) or []
        if skills:
            lines.append(f"{label}: {', '.join(skills)}")
    return "\n".join(lines)


def _format_price_line(price_info: dict[str, Any]) -> str:
    case_min = price_info.get("case_min")
    case_max = price_info.get("case_max")
    eng_price = price_info.get("engineer_price")
    gross = price_info.get("gross_profit")
    if case_min is not None and case_max is not None:
        range_text = f"{_format_man(case_min)}〜{_format_man(case_max)}万"
    elif case_max is not None:
        range_text = f"〜{_format_man(case_max)}万"
    else:
        range_text = "単価未設定"
    eng_text = f"{_format_man(eng_price)}万" if eng_price is not None else "単価未設定"
    gross_text = f"推定粗利: 約{gross}万円" if gross is not None else "粗利: 算出不可"
    estimate_note = "（推定単価あり）" if price_info.get("estimated") else ""
    return f"単価整合: 案件{range_text} / エンジニア{eng_text} / {gross_text}{estimate_note}"


def _format_start_line(start_info: dict[str, Any]) -> str:
    case_start = start_info.get("case_start")
    eng_start = start_info.get("engineer_start")
    if not case_start and not eng_start:
        return ""
    status = "整合" if start_info.get("aligned") else "要確認"
    return f"稼働時期: 案件{case_start or '未定'} / 人材{eng_start or '未定'}（{status}）"


def _format_parallel_status(engineer: dict[str, Any]) -> str:
    parallel_items = engineer.get("並行案件") or engineer.get("parallel_items") or []
    if parallel_items:
        parts = []
        for item in parallel_items:
            status = str(item.get("ステータス") or item.get("status") or "").strip()
            label = _PARALLEL_STATUS_LABELS.get(status, status or "不明")
            parts.append(f"1件（{label}）")
        return " / ".join(parts) if parts else "なし"

    memo = engineer.get("備考（LINEメモ）") or ""
    if not memo:
        return "なし"
    parts = []
    for status, label in _PARALLEL_STATUS_LABELS.items():
        if status in memo:
            parts.append(f"1件（{label}）")
    return " / ".join(parts) if parts else "なし"


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _format_man(value: Any) -> str:
    if value is None:
        return "?"
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return str(number)


def _gross_profit(case_max: Any, engineer_price: Any) -> float:
    if case_max is None or engineer_price is None:
        return 0.0
    return round(float(case_max) - float(engineer_price), 1)


def _initial(name: str) -> str:
    parts = [part for part in name.replace("　", " ").split(" ") if part]
    if len(parts) >= 2:
        return ".".join(part[0].upper() for part in parts[:2])
    return name[:2] if name else ""
