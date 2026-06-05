from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import dotenv_values

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "config" / ".env"

_ENV = dotenv_values(ENV_PATH, encoding="utf-8") if ENV_PATH.exists() else {}


def _get_model(env_name: str, default: str) -> str:
    return os.environ.get(env_name) or _ENV.get(env_name) or default


TEXT_MODEL = _get_model("TEXT_MODEL", "claude-haiku-4-5-20251001")
VISION_MODEL = _get_model("VISION_MODEL", "claude-sonnet-4-6")
STRUCTURER_MODEL = _get_model("STRUCTURER_MODEL", "gpt-4.1-nano")
MATCH_MODEL = _get_model("MATCH_MODEL", "claude-haiku-4-5-20251001")
