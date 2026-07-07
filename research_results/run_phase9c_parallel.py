# -*- coding: utf-8 -*-
"""Phase 9C 並列実行ランチャー"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
PY = sys.executable
BLOCK_EXIT_CODE = 2


def _start_worker(part: int, total: int, rate_limit: float, daily_limit: int) -> subprocess.Popen:
    cmd = [
        PY,
        "-u",
        str(BASE / "crawl_phase9c_screening.py"),
        "--part",
        str(part),
        "--total",
        str(total),
        "--rate-limit",
        str(rate_limit),
        "--daily-limit",
        str(daily_limit),
    ]
    print(f">>> {' '.join(cmd)}", flush=True)
    return subprocess.Popen(cmd, cwd=str(BASE))


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch parallel Phase 9C workers and merge results")
    parser.add_argument("--total", type=int, default=5, help="並列ワーカー数")
    parser.add_argument("--rate-limit", type=float, default=20.0, help="秒/クエリ（各ワーカー）")
    parser.add_argument("--daily-limit", type=int, default=500, help="1日あたり上限（全ワーカー合計）")
    parser.add_argument("--no-merge", action="store_true")
    parser.add_argument("--merge-only", action="store_true")
    args = parser.parse_args()

    if args.merge_only:
        return subprocess.call(
            [PY, "-u", str(BASE / "merge_phase9c.py"), "--total", str(args.total)],
            cwd=str(BASE),
        )

    per_worker_daily = max(1, args.daily_limit // args.total) if args.daily_limit > 0 else 0
    procs: list[tuple[int, subprocess.Popen]] = []
    for part in range(1, args.total + 1):
        procs.append((part, _start_worker(part, args.total, args.rate_limit, per_worker_daily)))

    blocked: list[int] = []
    failed: list[int] = []
    for part, proc in procs:
        rc = proc.wait()
        if rc == BLOCK_EXIT_CODE:
            blocked.append(part)
            print(f"[part{part}] stopped (Bing block)", flush=True)
        elif rc != 0:
            failed.append(part)
            print(f"[part{part}] exited {rc}", flush=True)
        else:
            print(f"[part{part}] completed", flush=True)

    if not args.no_merge:
        merge_rc = subprocess.call(
            [PY, "-u", str(BASE / "merge_phase9c.py"), "--total", str(args.total)],
            cwd=str(BASE),
        )
        if merge_rc:
            return merge_rc
        summary_rc = subprocess.call([PY, "-u", str(BASE / "write_phase9_summary.py")], cwd=str(BASE))
        if summary_rc:
            return summary_rc

    if blocked:
        print(f"Warning: parts {blocked} blocked by Bing — re-run later.", flush=True)
    return 1 if failed else (2 if blocked else 0)


if __name__ == "__main__":
    raise SystemExit(main())
