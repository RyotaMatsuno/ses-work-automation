#!/usr/bin/env python3
"""local_server Phase5: 実運用テスト（git status / write_and_run / matching.py）。"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SES_WORK = Path(__file__).resolve().parent.parent
BASE_URL = "http://127.0.0.1:8765"
AUTH_TOKEN = "jobz-terra-2026"


def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Auth-Token": AUTH_TOKEN,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _health() -> bool:
    req = urllib.request.Request(f"{BASE_URL}/health")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("status") == "ok"


def test_git_status() -> tuple[bool, str]:
    data = _post(
        "/run",
        {
            "cmd": "git status --short",
            "cwd": str(SES_WORK),
            "timeout": 30,
        },
    )
    if data.get("returncode") != 0:
        return False, f"git status failed: {data.get('stderr', '')}"
    return True, "git status OK"


def test_write_and_run() -> tuple[bool, str]:
    script_path = SES_WORK / "local_server" / "_phase5_test_script.py"
    data = _post(
        "/write_and_run",
        {
            "filepath": str(script_path),
            "content": 'print("PHASE5_OK")\n',
            "run_cmd": f'python "{script_path}"',
            "cwd": str(SES_WORK),
            "timeout": 30,
        },
    )
    if not data.get("written"):
        return False, "write failed"
    if data.get("returncode") != 0:
        return False, f"run failed: {data.get('stderr', '')}"
    if "PHASE5_OK" not in data.get("stdout", ""):
        return False, f"unexpected stdout: {data.get('stdout', '')!r}"
    try:
        script_path.unlink(missing_ok=True)
    except OSError:
        pass
    return True, "write_and_run OK"


def test_matching_py() -> tuple[bool, str]:
    data = _post(
        "/run",
        {
            "cmd": "python -m py_compile matching.py",
            "cwd": str(SES_WORK),
            "timeout": 30,
        },
    )
    if data.get("returncode") != 0:
        return False, f"matching.py compile failed: {data.get('stderr', '')}"
    return True, "matching.py OK (py_compile)"


def run_all() -> dict[str, tuple[bool, str]]:
    results: dict[str, tuple[bool, str]] = {}
    try:
        if not _health():
            return {"health": (False, "server not healthy")}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"health": (False, f"server unreachable: {exc}")}

    for name, fn in [
        ("git_status", test_git_status),
        ("write_and_run", test_write_and_run),
        ("matching_py", test_matching_py),
    ]:
        try:
            results[name] = fn()
        except Exception as exc:
            results[name] = (False, str(exc))
    return results


def main() -> int:
    results = run_all()
    all_ok = True
    for name, (ok, msg) in results.items():
        status = "OK" if ok else "NG"
        print(f"[{status}] {name}: {msg}")
        if not ok:
            all_ok = False
    if all_ok:
        print("VERIFY OK")
        return 0
    print("VERIFY NG")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
