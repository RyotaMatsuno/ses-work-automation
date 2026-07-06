# -*- coding: utf-8 -*-
"""Phase 4A→4E→5 一括実行オーケストレーター"""
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
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--rate-limit", type=float, default=10.0)
    parser.add_argument("--rate-limit-4e", type=float, default=20.0, help="Phase 4E用レート制限（秒）")
    parser.add_argument("--skip-4a", action="store_true")
    parser.add_argument("--skip-4b", action="store_true")
    parser.add_argument("--skip-4c", action="store_true")
    parser.add_argument("--skip-4d", action="store_true")
    parser.add_argument("--skip-4e", action="store_true")
    parser.add_argument("--merge-only", action="store_true")
    parser.add_argument("--limit-4c", type=int, default=0)
    parser.add_argument("--limit-4e", type=int, default=0)
    parser.add_argument("--priority-only-4e", action="store_true", help="4E: インセンティブ言及企業のみ")
    args = parser.parse_args()

    if args.merge_only:
        return _run("merge_all_channels.py")

    rc = 0
    if not args.skip_4a:
        rc = _run(
            "crawl_phase4a.py",
            "--site",
            "all",
            "--max-pages",
            str(args.max_pages),
            "--rate-limit",
            str(args.rate_limit),
        )
        if rc:
            print(f"phase4a exited {rc} (continuing)", flush=True)

    if not args.skip_4b:
        rc = _run("crawl_phase4b.py", "--rate-limit", str(args.rate_limit))
        if rc:
            print(f"phase4b exited {rc} (continuing)", flush=True)

    if not args.skip_4c:
        c_args = ["--rate-limit", str(args.rate_limit)]
        if args.limit_4c:
            c_args += ["--limit", str(args.limit_4c)]
        rc = _run("crawl_phase4c.py", *c_args)
        if rc:
            print(f"phase4c exited {rc} (continuing)", flush=True)

    if not args.skip_4d:
        rc = _run("crawl_phase4d.py", "--rate-limit", str(args.rate_limit))
        if rc:
            print(f"phase4d exited {rc} (continuing)", flush=True)

    if not args.skip_4e:
        e_args = ["--rate-limit", str(args.rate_limit_4e)]
        if args.limit_4e:
            e_args += ["--limit", str(args.limit_4e)]
        if args.priority_only_4e:
            e_args.append("--priority-only")
        rc = _run("crawl_phase4e.py", *e_args)
        if rc:
            print(f"phase4e exited {rc} (continuing)", flush=True)

    return _run("merge_all_channels.py")


if __name__ == "__main__":
    raise SystemExit(main())
