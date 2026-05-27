from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from step1_generate import generate_intent_drafts
from step2_send import send_intent_drafts
from step3_parse import parse_unread_replies
from step4_judge import judge_all
from step5_proposal import generate_proposals
from step6_send_proposal import send_proposals


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase1 営業パイプライン")
    parser.add_argument("--dry-run", action="store_true", help="メール送信と外部取得をスキップ")
    args = parser.parse_args()
    dry_run = bool(args.dry_run)
    try:
        generate_intent_drafts()
        send_intent_drafts(dry_run=dry_run)
        parse_unread_replies(dry_run=dry_run)
        judge_all()
        generate_proposals()
        send_proposals(dry_run=dry_run)
        return 0
    except Exception as exc:
        print(f"[pipeline] エラー: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
