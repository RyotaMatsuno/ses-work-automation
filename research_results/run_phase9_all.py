# -*- coding: utf-8 -*-
"""Phase 9 オーケストレーター（9A → 9B → 統合 → 9Cスクリーニング）"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
PY = sys.executable


def _run(script: str, *extra: str) -> int:
    cmd = [PY, "-u", str(BASE / script), *extra]
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=str(BASE))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 9 pipeline")
    parser.add_argument("--skip-9a", action="store_true")
    parser.add_argument("--skip-9b", action="store_true")
    parser.add_argument("--skip-merge", action="store_true")
    parser.add_argument("--skip-screening", action="store_true")
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--rate-limit", type=float, default=20.0)
    parser.add_argument("--daily-limit", type=int, default=500)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    if args.summary_only:
        return _run("write_phase9_summary.py")

    rc = 0
    if not args.skip_9a:
        r = _run("crawl_phase9a_gbiz.py")
        if r:
            print("[phase9] 9A skipped or failed (token未設定の場合は申請後に再実行)", flush=True)
            if r == 1:
                rc = r

    if not args.skip_9b:
        r = _run("crawl_phase9b_nta.py")
        if r:
            print("[phase9] 9B skipped or failed (ID未設定の場合は申請後に再実行)", flush=True)
            if r == 1:
                rc = rc or r

    if not args.skip_merge:
        r = _run("merge_phase9.py")
        if r:
            return r

    if not args.skip_screening:
        r = _run(
            "run_phase9c_parallel.py",
            "--total",
            str(args.workers),
            "--rate-limit",
            str(args.rate_limit),
            "--daily-limit",
            str(args.daily_limit),
        )
        if r not in (0, 2):
            return r

    return _run("write_phase9_summary.py") or rc


if __name__ == "__main__":
    raise SystemExit(main())
