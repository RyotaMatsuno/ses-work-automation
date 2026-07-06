# -*- coding: utf-8 -*-
"""Phase 7D 並列実行ランチャー（Windows / PowerShell 対応）"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
PY = sys.executable
BLOCK_EXIT_CODE = 2


def _start_worker(part: int, total: int, rate_limit: float) -> subprocess.Popen:
    cmd = [
        PY,
        "-u",
        str(BASE / "crawl_phase7d.py"),
        "--part",
        str(part),
        "--total",
        str(total),
        "--rate-limit",
        str(rate_limit),
    ]
    print(f">>> {' '.join(cmd)}", flush=True)
    return subprocess.Popen(cmd, cwd=str(BASE))


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch parallel Phase 7D workers and merge results")
    parser.add_argument("--total", type=int, default=5, help="並列ワーカー数")
    parser.add_argument("--rate-limit", type=float, default=20.0, help="秒/クエリ（各ワーカー）")
    parser.add_argument("--no-merge", action="store_true", help="完了後に merge_phase7d をスキップ")
    parser.add_argument("--merge-only", action="store_true", help="merge のみ実行")
    args = parser.parse_args()

    if args.merge_only:
        return subprocess.call([PY, "-u", str(BASE / "merge_phase7d.py"), "--total", str(args.total)], cwd=str(BASE))

    procs: list[tuple[int, subprocess.Popen]] = []
    for part in range(1, args.total + 1):
        procs.append((part, _start_worker(part, args.total, args.rate_limit)))

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

    print(
        f"\nWorkers done: ok={args.total - len(blocked) - len(failed)}, "
        f"blocked={blocked}, failed={failed}",
        flush=True,
    )

    if not args.no_merge:
        print("\n>>> merge_phase7d.py", flush=True)
        merge_rc = subprocess.call(
            [PY, "-u", str(BASE / "merge_phase7d.py"), "--total", str(args.total)],
            cwd=str(BASE),
        )
        if merge_rc:
            return merge_rc

    if blocked:
        print(f"Warning: parts {blocked} blocked by Bing — re-run those parts later.", flush=True)
    return 1 if failed else (2 if blocked else 0)


if __name__ == "__main__":
    raise SystemExit(main())
