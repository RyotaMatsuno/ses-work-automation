# -*- coding: utf-8 -*-
"""Phase 7 一括実行オーケストレーター"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
PY = sys.executable


def _run(script: str, *args: str) -> int:
    cmd = [PY, "-u", str(BASE / script), *args]
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=str(BASE))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate-limit", type=float, default=10.0)
    parser.add_argument("--rate-limit-7d", type=float, default=20.0)
    parser.add_argument("--daily-limit-7d", type=int, default=500)
    parser.add_argument("--skip-7a", action="store_true")
    parser.add_argument("--skip-7b", action="store_true")
    parser.add_argument("--skip-7c", action="store_true")
    parser.add_argument("--skip-7d", action="store_true")
    parser.add_argument("--parallel-7d", action="store_true", help="7Dを5並列で実行")
    parser.add_argument("--workers-7d", type=int, default=5, help="7D並列ワーカー数")
    parser.add_argument("--merge-only", action="store_true")
    args = parser.parse_args()

    if args.merge_only:
        rc = _run("merge_phase7c.py")
        if rc:
            return rc
        return _run("merge_phase7.py")

    if not args.skip_7a:
        rc = _run("crawl_phase7a.py", "--rate-limit", str(args.rate_limit))
        if rc:
            print(f"phase7a exited {rc} (continuing)", flush=True)

    if not args.skip_7b:
        rc = _run("crawl_phase7b.py", "--rate-limit", str(args.rate_limit))
        if rc:
            print(f"phase7b exited {rc} (continuing)", flush=True)

    if not args.skip_7c:
        rc = _run("merge_phase7c.py")
        if rc:
            print(f"merge_phase7c exited {rc} (continuing)", flush=True)

    if not args.skip_7d:
        if args.parallel_7d:
            rc = _run(
                "run_phase7d_parallel.py",
                "--total",
                str(args.workers_7d),
                "--rate-limit",
                str(args.rate_limit_7d),
            )
        else:
            rc = _run(
                "crawl_phase7d.py",
                "--rate-limit",
                str(args.rate_limit_7d),
                "--daily-limit",
                str(args.daily_limit_7d),
            )
        if rc:
            print(f"phase7d exited {rc} (continuing)", flush=True)

    return _run("merge_phase7.py")


if __name__ == "__main__":
    raise SystemExit(main())
