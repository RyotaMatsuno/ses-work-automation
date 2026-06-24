from __future__ import annotations

import logging
from typing import Any, Callable

from common.io_utils import setup_stdout

setup_stdout()

logger = logging.getLogger(__name__)


class ExitCode2(Exception):
    """exit code 2（スキップ）を示す内部例外。"""

    def __init__(self, reason: str = "", detail: str = ""):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def run_with_skip(fn: Callable, *args: Any, **kwargs: Any) -> Any | None:
    """fn を実行し、ExitCode2 が発生した場合はスキップして None を返す（SPEC §7, exit code 2）。

    使用例:
        result = run_with_skip(skill_judge, required, engineer_skills)
        if result is None:
            continue  # skipped
    """
    try:
        return fn(*args, **kwargs)
    except ExitCode2 as e:
        logger.info("[exit_handler] skipped: reason=%s detail=%s", e.reason, e.detail)
        return None
    except SystemExit as e:
        if e.code == 2:
            logger.info("[exit_handler] exit(2) caught, treating as skip")
            return None
        raise
