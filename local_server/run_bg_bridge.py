"""
run_bg_bridge.py - /run_bg エンドポイントを叩くブリッジ
"""

import json
import sys
import urllib.error
import urllib.request

TOKEN = "jobz-terra-2026"
BASE = "http://127.0.0.1:8765"


def run_bg(cmd, cwd=None, job_id=None):
    payload = {"cmd": cmd}
    if cwd:
        payload["cwd"] = cwd
    if job_id:
        payload["job_id"] = job_id
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/run_bg",
        data=data,
        headers={"Content-Type": "application/json", "X-Auth-Token": TOKEN},
        method="POST",
    )
    try:
        r = urllib.request.urlopen(req, timeout=10)
        print(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}")
    except Exception as e:
        print(f"ERROR: {e}")


def get_log(job_id, lines=50):
    req = urllib.request.Request(
        f"{BASE}/log?job_id={job_id}&lines={lines}",
        headers={"X-Auth-Token": TOKEN},
    )
    try:
        r = urllib.request.urlopen(req, timeout=10)
        print(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "help"
    if action == "test_bg":
        run_bg("echo bg_test_ok", job_id="test_001")
    elif action == "get_log":
        get_log(sys.argv[2] if len(sys.argv) > 2 else "test_001")
    elif action == "codex":
        # codex exec で非インタラクティブ起動（-C オプションなし、cwdで制御）
        target_dir = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline"
        cmd = 'codex exec "SPEC_opt.mdとCLAUDE_opt.mdを読んでTASKS_opt.mdの順番でmail_pipeline.pyを改修してください" --dangerously-bypass-approvals-and-sandbox'
        run_bg(cmd, cwd=target_dir, job_id="codex_opt_002")
    else:
        print("Usage: python run_bg_bridge.py [test_bg|get_log <job_id>|codex]")
