"""
Claude Code をバックグラウンドで起動し、ログをファイルに書き出す。
27分制限を回避するため subprocess.Popen + DETACHED_PROCESS で投げっぱなしにし、
別途ログを polling する戦略。
"""

import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ses_work = os.getcwd()
prompt_file = os.path.join(ses_work, "task_auto_runner", "_bootstrap_prompt.txt")
log_file = os.path.join(ses_work, "task_auto_runner", "logs", "bootstrap_run.log")
err_file = os.path.join(ses_work, "task_auto_runner", "logs", "bootstrap_err.log")

# プロンプト読み込み
with open(prompt_file, encoding="utf-8") as f:
    prompt_text = f.read()

# Claude Code 呼び出し
# claude.cmd を直接呼ぶ
cmd = [
    "claude",
    "-p",
    prompt_text,
    "--dangerously-skip-permissions",
    "--model",
    "sonnet",
    "--max-budget-usd",
    "5",
    "--output-format",
    "json",
    "--no-session-persistence",
    "--add-dir",
    ses_work,
]

# DETACHED_PROCESS でバックグラウンド起動
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

with open(log_file, "wb") as out, open(err_file, "wb") as err:
    proc = subprocess.Popen(
        cmd,
        stdout=out,
        stderr=err,
        cwd=ses_work,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        shell=True,  # Windowsでclaude.cmd経由
    )
    # PID保存
    with open(os.path.join(ses_work, "task_auto_runner", "logs", "bootstrap.pid"), "w") as f:
        f.write(str(proc.pid))

print(f"Claude Code started, PID={proc.pid}")
print(f"log: {log_file}")
print(f"err: {err_file}")
