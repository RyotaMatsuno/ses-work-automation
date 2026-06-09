"""Screenshot OCR with sensitive text masking."""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PASSWORD_PATTERNS = [
    re.compile(r"(?i)(password|passwd|パスワード|pwd)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*\S+"),
]
CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
MASK = "[MASKED]"

_TESSERACT_PATHS = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
]


def configure_tesseract() -> bool:
    try:
        import pytesseract
    except ImportError:
        return False

    for path in _TESSERACT_PATHS:
        if path.exists():
            pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            return True
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _mask_credential(match: re.Match[str]) -> str:
    value = match.group(0)
    if "=" in value:
        return value.split("=", 1)[0] + f"={MASK}"
    if ":" in value:
        return value.split(":", 1)[0] + f": {MASK}"
    return MASK


def mask_sensitive_text(text: str) -> str:
    masked = text
    for pattern in PASSWORD_PATTERNS:
        masked = pattern.sub(_mask_credential, masked)
    return CARD_PATTERN.sub(MASK, masked)


def extract_text(image_path: str | Path, lang: str = "jpn+eng") -> str:
    path = Path(image_path)
    if not path.exists():
        return ""

    if not configure_tesseract():
        return ""

    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return ""

    try:
        with Image.open(path) as img:
            raw = pytesseract.image_to_string(img, lang=lang)
    except Exception:
        return ""

    cleaned = mask_sensitive_text(raw.strip())
    return cleaned
