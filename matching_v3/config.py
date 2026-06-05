from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import yaml
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.model_config import STRUCTURER_MODEL


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / "config" / ".env"
USERS_PATH = BASE_DIR / "users.yaml"

ENGINEER_DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
CASE_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
DEFAULT_STRUCTURER_MODEL = STRUCTURER_MODEL


class Config:
    def __init__(self, env_path: str | Path = ENV_PATH, users_path: str | Path = USERS_PATH) -> None:
        self.env_path = Path(env_path)
        self.users_path = Path(users_path)
        self.env = dict(dotenv_values(self.env_path, encoding="utf-8"))
        self.users = self._load_users(self.users_path)
        self.engineer_db_id = ENGINEER_DB_ID
        self.case_db_id = CASE_DB_ID
        self.structurer_model = os.environ.get(
            "STRUCTURER_MODEL",
            self.env.get("STRUCTURER_MODEL") or DEFAULT_STRUCTURER_MODEL,
        )

    def get(self, key: str, default: str | None = None) -> str | None:
        return os.environ.get(key) or self.env.get(key) or default

    @property
    def notion_api_key(self) -> str | None:
        return self.get("NOTION_API_KEY")

    @property
    def anthropic_api_key(self) -> str | None:
        return self.get("ANTHROPIC_API_KEY")

    @property
    def line_channel_access_token(self) -> str | None:
        return self.get("LINE_CHANNEL_ACCESS_TOKEN")

    @staticmethod
    def _load_users(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"users.yaml not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        users = data.get("users")
        if not isinstance(users, dict):
            raise ValueError("users.yaml must contain a 'users' mapping")
        return users
