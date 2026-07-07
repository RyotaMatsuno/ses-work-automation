#!/usr/bin/env python3
"""Copy scripts/hooks/pre-push into .git/hooks/pre-push and make it executable."""
import sys
import shutil
import stat
import subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    repo_root = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], encoding="utf-8"
        ).strip()
    )

    src = repo_root / "scripts" / "hooks" / "pre-push"
    dst = repo_root / ".git" / "hooks" / "pre-push"

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    dst.chmod(dst.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Installed: {dst}")


if __name__ == "__main__":
    main()
