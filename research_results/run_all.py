# -*- coding: utf-8 -*-
"""全Phase実行オーケストレーター"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
PY = sys.executable


def run(cmd: list[str]) -> int:
    print(">>>", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(BASE.parent))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--max-pages", type=int, default=20)
    p.add_argument("--rate-phase1", type=float, default=5.0)
    p.add_argument("--rate-phase2", type=float, default=10.0)
    p.add_argument("--phase", type=int, default=0, help="0=all, 1/2/3/merge only")
    p.add_argument("--rules-only", action="store_true", help="Phase3: LLMなしルール抽出")
    p.add_argument("--skip-search", action="store_true")
    args = p.parse_args()

    scripts = {
        1: [PY, str(BASE / "crawl_phase1.py"), "--direct-only", "--max-pages", str(args.max_pages), "--rate-limit", str(args.rate_phase1)],
        2: [PY, str(BASE / "crawl_phase2_engage.py"), "--max-pages", str(args.max_pages), "--rate-limit", str(args.rate_phase2)],
        3: [PY, str(BASE / "extract_phase3.py"), "--rate-limit", str(args.rate_phase2)] + (["--rules-only"] if args.rules_only else []),
        4: [PY, str(BASE / "merge_and_report.py")],
    }
    if args.skip_search:
        scripts[1].append("--skip-search")

    phases = [args.phase] if args.phase else [1, 2, 3, 4]
    for ph in phases:
        if ph == 2:
            run([PY, str(BASE / "crawl_phase2_green.py"), "--rate-limit", str(args.rate_phase2)])
        rc = run(scripts[ph])
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
