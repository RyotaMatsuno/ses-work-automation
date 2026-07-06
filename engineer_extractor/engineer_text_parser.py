"""Engineer text parser — detects 3 patterns and segments text into structured fields."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PATTERN_AUTO_IMPORT = "auto_import"
PATTERN_EMAIL_REGISTER = "email_register"
PATTERN_LINE_REGISTER = "line_register"
PATTERN_UNKNOWN = "unknown"

_LABELED_FIELD_KEYS = [
    "スキル", "単価", "最寄", "最寄り駅", "最寄駅", "開始", "名前", "所属",
    "並行", "資格", "経験", "備考", "希望単価", "稼動可能日", "稼働可能日",
    "性別", "年齢", "国籍",
]

_LABELED_RE = re.compile(
    r"【(" + "|".join(re.escape(k) for k in _LABELED_FIELD_KEYS) + r")】([^\n【]*)"
    r"|(?:^|\n)(" + "|".join(re.escape(k) for k in _LABELED_FIELD_KEYS) + r")[：:]\s*([^\n]*)",
)


@dataclass
class ParsedEngineerText:
    pattern_type: str
    subject: str | None
    body: str
    labeled_fields: dict[str, str] = field(default_factory=dict)
    sender: str | None = None
    received_date: str | None = None
    full_text: str = ""


def _extract_line_value(text: str, key: str) -> str | None:
    m = re.search(rf"(?:^|\n){re.escape(key)}\s*[:：]\s*([^\n]+)", text)
    return m.group(1).strip() if m else None


def _extract_labeled_fields(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for m in re.finditer(
        r"【(" + "|".join(re.escape(k) for k in _LABELED_FIELD_KEYS) + r")】([^\n【]*)",
        text,
    ):
        result[m.group(1).strip()] = m.group(2).strip()
    for k in _LABELED_FIELD_KEYS:
        if k not in result:
            v = _extract_line_value(text, k)
            if v:
                result[k] = v
    return result


def _parse_auto_import(text: str) -> ParsedEngineerText:
    subject = None
    m = re.search(r"件名[:：]\s*(.+)", text)
    if m:
        subject = m.group(1).strip()

    sender = None
    m = re.search(r"送信元[:：]\s*(.+)", text)
    if m:
        sender = m.group(1).strip()

    received_date = None
    m = re.search(r"受信日[:：]\s*(.+)", text)
    if m:
        received_date = m.group(1).strip()

    # body = everything after the header block
    header_end = max(
        (text.find("\n", text.find("受信日")) if "受信日" in text else -1),
        (text.find("\n", text.find("送信元")) if "送信元" in text else -1),
    )
    body = text[header_end + 1:].strip() if header_end >= 0 else text

    return ParsedEngineerText(
        pattern_type=PATTERN_AUTO_IMPORT,
        subject=subject,
        body=body,
        labeled_fields=_extract_labeled_fields(text),
        sender=sender,
        received_date=received_date,
        full_text=text,
    )


def _parse_email_register(text: str) -> ParsedEngineerText:
    subject = None
    m = re.search(r"件名[:：]\s*(.+)", text)
    if m:
        subject = m.group(1).strip()

    sender = None
    m = re.search(r"送信者[:：]\s*(.+)", text)
    if m:
        sender = m.group(1).strip()

    # body = lines after the header keywords
    lines = text.splitlines()
    header_kws = {"【メールから自動登録】", "送信者", "件名"}
    body_lines = []
    header_done = False
    for line in lines:
        stripped = line.strip()
        if not header_done:
            if any(stripped.startswith(kw) for kw in header_kws) or stripped == "【メールから自動登録】":
                continue
            header_done = True
        body_lines.append(line)
    body = "\n".join(body_lines).strip()

    return ParsedEngineerText(
        pattern_type=PATTERN_EMAIL_REGISTER,
        subject=subject,
        body=body,
        labeled_fields=_extract_labeled_fields(text),
        sender=sender,
        received_date=None,
        full_text=text,
    )


def _parse_line_register(text: str) -> ParsedEngineerText:
    labeled_fields = _extract_labeled_fields(text)
    return ParsedEngineerText(
        pattern_type=PATTERN_LINE_REGISTER,
        subject=None,
        body=text,
        labeled_fields=labeled_fields,
        sender=None,
        received_date=None,
        full_text=text,
    )


def parse_engineer_text(text: str) -> ParsedEngineerText:
    if not text or not text.strip():
        return ParsedEngineerText(
            pattern_type=PATTERN_UNKNOWN,
            subject=None,
            body="",
            full_text=text or "",
        )

    if "[自動取込]" in text:
        return _parse_auto_import(text)

    if "【メールから自動登録】" in text:
        return _parse_email_register(text)

    if re.search(r"\[LINE登録[:：]|\[LINE auto-register[:：]", text):
        return _parse_line_register(text)

    labeled_fields = _extract_labeled_fields(text)
    if re.search(r"【(スキル|単価|名前|最寄)】", text):
        return ParsedEngineerText(
            pattern_type=PATTERN_LINE_REGISTER,
            subject=None,
            body=text,
            labeled_fields=labeled_fields,
            sender=None,
            received_date=None,
            full_text=text,
        )

    # fallback: try to extract labeled fields from any format
    return ParsedEngineerText(
        pattern_type=PATTERN_UNKNOWN,
        subject=None,
        body=text,
        labeled_fields=labeled_fields,
        full_text=text,
    )
