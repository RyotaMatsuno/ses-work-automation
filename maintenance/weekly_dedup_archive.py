"""週次 cron: dedup_claims の confirmed=1 履歴を dedup_claims_archive へ移動する。

Task Scheduler または cron で週1回実行する（TASKS.md §4.4）:
  Windows: schtasks /create /sc WEEKLY /tn "dedup_archive" /tr "python path/weekly_dedup_archive.py"
  Linux:   0 2 * * 0 python /path/to/weekly_dedup_archive.py

exit 0 = 正常 / exit 1 = エラー
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sys as _sys
try:
    from common.io_utils import setup_stdout
    setup_stdout()
except Exception:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    try:
        from common.dedup import archive_confirmed_dedup_claims
        archived = archive_confirmed_dedup_claims()
        logger.info("dedup_archive: %d claim(s) moved to dedup_claims_archive", archived)
        return 0
    except Exception as exc:
        logger.error("dedup_archive failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
