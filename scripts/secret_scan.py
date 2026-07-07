#!/usr/bin/env python3
"""git pre-push secret scanner. Exits 1 if secrets detected. Values are never printed."""
import sys
import re
import subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PATTERNS = [
    ("OpenAI key",         re.compile(rb"sk-[A-Za-z0-9_\-]{20,}")),
    ("GCP API key",        re.compile(rb"AIza[0-9A-Za-z_\-]{30,}")),
    ("Private key",        re.compile(rb"-----BEGIN [A-Z ]+ PRIVATE KEY")),
    ("GCP OAuth token",    re.compile(rb"ya29\.[A-Za-z0-9_\-]{30,}")),
    ("LINE channel token", re.compile(rb"[A-Za-z0-9/+=]{140,}")),
]


def get_push_files() -> list[str]:
    """Return file paths (Added/Modified) in push range vs origin/main."""
    for ref in ("origin/main..HEAD", "origin/master..HEAD"):
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=AM", ref],
            capture_output=True,
        )
        if result.returncode == 0:
            files = result.stdout.decode("utf-8", errors="replace").strip().split("\n")
            return [f for f in files if f]
    return []


def scan_bytes(raw: bytes) -> list[tuple[str, int]]:
    """Scan raw bytes for secret patterns. Returns (pattern_name, line_number) pairs."""
    # Strip null bytes for UTF-16 detection (preserves line structure approximately)
    if b"\x00" in raw[:200]:
        body = raw.replace(b"\x00", b"")
    else:
        body = raw

    hits = []
    for name, pattern in PATTERNS:
        for match in pattern.finditer(body):
            line_num = body[: match.start()].count(b"\n") + 1
            hits.append((name, line_num))
    return hits


def scan_file(filepath: str) -> list[tuple[str, int]]:
    """Scan a single file. Returns (pattern_name, line_number) pairs."""
    try:
        raw = Path(filepath).read_bytes()
    except (IOError, OSError):
        return []
    return scan_bytes(raw)


def main() -> None:
    files = get_push_files()
    if not files:
        sys.exit(0)

    found = False
    for filepath in files:
        hits = scan_file(filepath)
        for pattern_name, line_num in hits:
            # Print only file + line — never the secret value itself
            print(f"[BLOCKED] {filepath}:{line_num} — {pattern_name} detected")
            found = True

    if found:
        print("\nPush blocked: remove secrets and retry.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
