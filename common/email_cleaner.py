from __future__ import annotations

import re

_SIGNATURE_MARKERS = re.compile(r"^--\s*$|^――――+|^────────────────+", re.MULTILINE)
_CONTACT_LINE = re.compile(
    r"^(?:TEL|Tel|tel|携帯|電話|FAX|Fax|fax|HP|ＨＰ|http|https|Mail|mail|E-?mail)\s*[:：]",
    re.MULTILINE | re.IGNORECASE,
)
_DISCLAIMER = re.compile(
    r"本メールは.*?送信専用|このメールは.*?宛てに送信|誤送信.*?削除|配信停止",
    re.DOTALL,
)
_QUOTED_REPLY = re.compile(
    r"^>.*$|^-{2,}\s*Original Message\s*-{2,}|^On .+ wrote:\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_DECORATION_ONLY = re.compile(r"^[★☆■□▲▼◆◇●○◎━─═＝\s]+$")
_MULTI_BLANK = re.compile(r"\n{3,}")


def remove_signature(body: str) -> str:
    match = _SIGNATURE_MARKERS.search(body)
    if match:
        body = body[: match.start()]
    lines: list[str] = []
    for line in body.splitlines():
        if _CONTACT_LINE.match(line.strip()):
            break
        lines.append(line)
    return "\n".join(lines)


def remove_disclaimer(body: str) -> str:
    match = _DISCLAIMER.search(body)
    if match:
        body = body[: match.start()]
    return body


def remove_quoted_reply(body: str) -> str:
    lines = []
    for line in body.splitlines():
        if _QUOTED_REPLY.match(line.strip()):
            break
        lines.append(line)
    return "\n".join(lines)


def remove_decoration(body: str) -> str:
    kept = [line for line in body.splitlines() if not _DECORATION_ONLY.match(line.strip())]
    return "\n".join(kept)


def normalize_whitespace(body: str) -> str:
    return _MULTI_BLANK.sub("\n\n", body)


def clean_email_body(body: str) -> str:
    body = remove_signature(body)
    body = remove_disclaimer(body)
    body = remove_quoted_reply(body)
    body = remove_decoration(body)
    body = normalize_whitespace(body)
    return body.strip()
