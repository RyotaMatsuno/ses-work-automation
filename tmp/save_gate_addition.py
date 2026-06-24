def _run_gate_on_save(content, title):
    import os
    import subprocess
    import sys
    import tempfile

    base = os.path.join(os.path.expanduser("~"), "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix="gate_tmp_")
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        gate_script = os.path.join(base, "gate_checker", "gate_check.py")
        result = subprocess.run(
            [sys.executable, gate_script, "--phase", "requirements", "--file", tmp_path],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            cwd=base,
            timeout=60,
        )
        output = (result.stdout or "") + (result.stderr or "")
        lines = [l for l in output.splitlines() if l.strip()]
        summary = "\n".join(lines[-5:]) if lines else "(出力なし)"
        print(f"[gate] exit={result.returncode}\n{summary}")
        return result.returncode, summary
    except subprocess.TimeoutExpired:
        print("[gate] タイムアウト -> スキップして保存")
        return 2, "timeout"
    except Exception as e:
        print(f"[gate] エラー -> スキップして保存: {e}")
        return 2, str(e)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _notify_gate_ng(filename, summary):
    env = _load_env()
    token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = env.get("MATSUNO_LINE_USER_ID") or env.get("MATSUNO_USER_ID", "")
    if not token or not user_id:
        return
    message = "\U0001f6ab [gate NG] save blocked\n" + filename + "\n\n" + summary[:300]
    payload = json.dumps(
        {"to": user_id, "messages": [{"type": "text", "text": message}]},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            print(f"gate NG LINE通知: {res.status}")
    except Exception as e:
        print(f"gate NG LINE通知失敗: {e}")


def save_task(title, content, gate_on_save=True):
    """指示書をpending_tasks/に保存。gate_on_save=True(default)でゲートを自動実行。"""
    os.makedirs(PENDING_DIR, exist_ok=True)
    num = get_next_number()
    filename = f"{num:03d}_{title}.md"
    if gate_on_save:
        exit_code, summary = _run_gate_on_save(content, title)
        if exit_code == 1:
            print(f"[gate NG] {filename} の保存をブロック")
            _notify_gate_ng(filename, summary)
            return f"GATE_NG:{filename}"
        if exit_code == 2:
            print("[gate] スキップ -> そのまま保存")
    filepath = os.path.join(PENDING_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"保存完了（ゲート通過）: {filename}")
    return filename
