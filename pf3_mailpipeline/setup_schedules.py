"""
setup_schedules.py - Phase3 scheduler setup

SES_MailPipeline and SES_MatchingV3 intervals are changed with schtasks.
"""

import subprocess
import sys

TASKS = [
    ("SES_MailPipeline", "60"),
    ("SES_MatchingV3", "120"),
]


def run_command(args: list[str]) -> int:
    print(f"> {' '.join(args)}", flush=True)
    completed = subprocess.run(
        args,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if completed.stdout:
        print(completed.stdout.strip())
    if completed.stderr:
        print(completed.stderr.strip(), file=sys.stderr)
    return completed.returncode


def main() -> int:
    exit_code = 0
    for task_name, interval in TASKS:
        code = run_command(["schtasks", "/Change", "/TN", task_name, "/RI", interval])
        if code != 0:
            exit_code = code
        code = run_command(["schtasks", "/Query", "/TN", task_name, "/FO", "LIST"])
        if code != 0:
            exit_code = code
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
