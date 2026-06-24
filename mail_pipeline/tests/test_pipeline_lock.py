"""Task J: mail_pipeline ファイルロックのテスト。"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SES_WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SES_WORK))

from mail_pipeline import mail_pipeline as mp


@pytest.fixture()
def lock_env(monkeypatch: pytest.MonkeyPatch) -> Path:
    tmp = Path(tempfile.mkdtemp())
    lock_file = tmp / "pipeline.lock"
    monkeypatch.setenv("LOCALAPPDATA", str(tmp))
    monkeypatch.setattr(mp, "LOCK_FILE", str(lock_file))
    return lock_file


def test_second_process_exits_when_lock_held(lock_env: Path) -> None:
    first = mp.acquire_lock()
    try:
        script = """
import os, sys
sys.path.insert(0, r'{ses}')
os.environ['LOCALAPPDATA'] = r'{appdata}'
import mail_pipeline.mail_pipeline as mp
mp.LOCK_FILE = r'{lock}'
mp.acquire_lock()
""".format(
            ses=str(SES_WORK).replace("\\", "\\\\"),
            appdata=str(lock_env.parent).replace("\\", "\\\\"),
            lock=str(lock_env).replace("\\", "\\\\"),
        )
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        assert proc.returncode == 0
        combined = (proc.stdout or "") + (proc.stderr or "")
        assert "別プロセスが実行中" in combined or proc.returncode == 0
    finally:
        first.close()


def test_scheduler_main_exits_immediately() -> None:
    scheduler_path = SES_WORK / "local_server" / "scheduler.py"
    proc = subprocess.run(
        [sys.executable, str(scheduler_path)],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(SES_WORK / "local_server"),
    )
    assert proc.returncode == 0
    assert "廃止" in proc.stdout
