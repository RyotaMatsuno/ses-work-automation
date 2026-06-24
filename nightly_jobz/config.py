"""nightly_jobz 設定値."""

from __future__ import annotations

import os
from pathlib import Path

SES_WORK = Path(os.environ.get("USERPROFILE", "")) / "OneDrive" / "デスクトップ" / "ses_work"
ENV_PATH = SES_WORK / "config" / ".env"
RESEARCH_DIR = SES_WORK / "research_results"
DRAFTS_DIR = Path(__file__).resolve().parent / "drafts"

NIGHTLY_LOCK_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "ses_work_state",
    "nightly_jobz.lock",
)
MAX_RUNTIME_SECONDS = 7200
QUEUE_DB_ID = "37a450ff-37c0-819a-981b-c2e06ed282bb"
LOG_DIR = Path(__file__).resolve().parent / "logs"
NOTION_VERSION = "2022-06-28"
BLOCK_TYPE = "nightly_jobz"
GPT_MODEL = "gpt-5.4"
LOG_RETENTION_DAYS = 7

# DRY_RUN は関数経由で取得（モジュールレベル評価のバグ防止）
# デフォルト: True（安全側）。本番は NIGHTLY_DRY_RUN=0 + ALLOW_PROD_WRITES=YES 必須。
def get_dry_run() -> bool:
    val = os.environ.get("NIGHTLY_DRY_RUN")
    if val is None:
        return True  # 未設定 = DRY_RUN
    return val.strip().lower() in {"1", "true", "yes", "on"}
def get_nightly_budget() -> float:
    """Nightly budget (module-level eval bug prevention)."""
    return float(os.environ.get("COST_GUARD_NIGHTLY_USD", "2.0"))

NIGHTLY_BUDGET_USD = None  # deprecated, use get_nightly_budget()


def load_env() -> None:
    if not ENV_PATH.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH)
    except ImportError:
        pass


class RunCostTracker:
    """1実行あたりのnightly予算トラッカー。"""

    def __init__(self, limit_usd: float | None = None) -> None:
        self.limit_usd = limit_usd if limit_usd is not None else get_nightly_budget()
        self.total_usd = 0.0

    def can_spend(self, estimated_usd: float = 0.0) -> bool:
        return (self.total_usd + estimated_usd) <= self.limit_usd

    def add(self, usd: float) -> None:
        self.total_usd += max(0.0, usd)
