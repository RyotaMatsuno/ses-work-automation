# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES_WORK = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

targets = [
    ("--file", "matching_v2/skill_judge.py"),
    ("--file", "gate_checker/agreement_checker.py"),
]

for flag, target in targets:
    print(f"\n{'=' * 60}")
    print(f"ゲート② {target}")
    print("=" * 60)
    r = subprocess.run(
        [sys.executable, "gate_checker/gate_check.py", "--phase", "implementation", flag, target],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=SES_WORK,
        timeout=180,
    )
    print(r.stdout[-2000:] if len(r.stdout) > 2000 else r.stdout)
    if r.stderr:
        print("STDERR:", r.stderr[-500:])
    print(f"returncode: {r.returncode}")
