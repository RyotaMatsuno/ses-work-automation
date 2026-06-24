#!/usr/bin/env python3
"""task_runner.py パッチ: save時にゲート①を自動実行"""
import sys, os, shutil, subprocess, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = os.path.join(os.path.expanduser("~"), "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
tr_path = os.path.join(base, "local_server", "task_runner.py")

src = open(tr_path, encoding="utf-8").read()

if "gate_on_save" in src:
    print("既にパッチ済みです。スキップ。")
    sys.exit(0)

shutil.copy(tr_path, tr_path + ".bak")
print("backup OK")

# save_task関数を丸ごと差し替え
old_save = '''def save_task(title: str, content: str) -> str:
    """指示書をpending_tasks/に保存"""
    os.makedirs(PENDING_DIR, exist_ok=True)
    num = get_next_number()
    filename = f"{num:03d}_{title}.md"
    filepath = os.path.join(PENDING_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"保存完了: {filename}")
    return filename'''

new_save = '''def _run_gate_on_save(content: str, title: str) -> tuple[int, str]:
    """save前にgate_checker requirements を自動実行（タイムアウト60s）。
    戻り値: (exit_code, summary)
      exit 0 = GO
      exit 1 = NG → pending_tasksに保存しない
      exit 2 = エラー/スキップ → そのまま保存
    """
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix="gate_tmp_")
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)

        gate_script = os.path.join(BASE_DIR, "gate_checker", "gate_check.py")
        result = subprocess.run(
            [sys.executable, gate_script, "--phase", "requirements", "--file", tmp_path],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            cwd=BASE_DIR,
            timeout=60,
        )
        output = (result.stdout or "") + (result.stderr or "")
        # サマリー抽出（最後の5行）
        lines = [l for l in output.splitlines() if l.strip()]
        summary = "\\n".join(lines[-5:]) if lines else "(出力なし)"
        print(f"[gate①] exit={result.returncode}\\n{summary}")
        return result.returncode, summary
    except subprocess.TimeoutExpired:
        print("[gate①] タイムアウト → スキップして保存")
        return 2, "timeout"
    except Exception as e:
        print(f"[gate①] エラー → スキップして保存: {e}")
        return 2, str(e)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _notify_gate_ng(filename: str, summary: str) -> None:
    """ゲートNG時に松野のLINEへ通知。"""
    env = _load_env()
    token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = env.get("MATSUNO_LINE_USER_ID") or env.get("MATSUNO_USER_ID", "")
    if not token or not user_id:
        return
    message = f"\u{1F6AB} [ゲートNG] タスク保存をブロックしました\\nファイル: {filename}\\n\\n{summary[:300]}"
    payload = json.dumps(
        {"to": user_id, "messages": [{"type": "text", "text": message}]},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            print(f"ゲートNG LINE通知: {res.status}")
    except Exception as e:
        print(f"ゲートNG LINE通知失敗: {e}")


def save_task(title: str, content: str, gate_on_save: bool = True) -> str:
    """指示書をpending_tasks/に保存。gate_on_save=True(デフォルト)でゲート①を自動実行。"""
    os.makedirs(PENDING_DIR, exist_ok=True)
    num = get_next_number()
    filename = f"{num:03d}_{title}.md"

    if gate_on_save:
        exit_code, summary = _run_gate_on_save(content, title)
        if exit_code == 1:
            # NG → 保存せずLINE通知してブロック
            print(f"[gate①] NG → {filename} の保存をブロック")
            _notify_gate_ng(filename, summary)
            return f"GATE_NG:{filename}"
        # exit 0 (GO) または exit 2 (エラースキップ) → 保存続行
        if exit_code == 2:
            print(f"[gate①] スキップ → そのまま保存")

    filepath = os.path.join(PENDING_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"保存完了（ゲート通過）: {filename}")
    return filename'''

src = src.replace(old_save, new_save)

# Unicode絵文字エスケープ修正
src = src.replace(r"\u{1F6AB}", "\U0001F6AB")

open(tr_path, "w", encoding="utf-8").write(src)
print("task_runner.py パッチ完了")

# 構文チェック
r = subprocess.run([sys.executable, "-m", "py_compile", tr_path], capture_output=True, encoding="utf-8")
if r.returncode == 0:
    print("構文チェック OK")
else:
    print("構文エラー:", r.stderr)
    shutil.copy(tr_path + ".bak", tr_path)
    print("バックアップから復元しました")
