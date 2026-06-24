import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 既存PIDがあれば残骸として除去
pid_file = "task_auto_runner/logs/bootstrap.pid"
if os.path.exists(pid_file):
    os.remove(pid_file)

with open("task_auto_runner/_bootstrap_prompt.txt", encoding="utf-8") as f:
    prompt_text = f.read()

ses_work = os.getcwd()

# プロンプトを stdin から渡す方式に変更
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

print(f"[{time.strftime('%H:%M:%S')}] Claude Code 起動")
start = time.time()

# subprocess.run でフォアグラウンド、shell=True で claude.cmd 経由
result = subprocess.run(
    cmd,
    capture_output=True,
    text=False,  # バイナリで受けて後でデコード
    cwd=ses_work,
    timeout=1500,
    shell=False,
)

duration = time.time() - start
print(f"[{time.strftime('%H:%M:%S')}] 完了, duration={duration:.1f}s, exit={result.returncode}")

# 結果保存
with open("task_auto_runner/logs/bootstrap_run.log", "wb") as f:
    f.write(result.stdout)
with open("task_auto_runner/logs/bootstrap_err.log", "wb") as f:
    f.write(result.stderr)

# stdoutの最後だけ表示（JSON結果のはず）
out_text = result.stdout.decode("utf-8", errors="replace")
err_text = result.stderr.decode("utf-8", errors="replace")

print(f"\nstdout size: {len(out_text)} chars")
print(f"stderr size: {len(err_text)} chars")
print("\n--- stdout tail ---")
print(out_text[-3000:])
print("\n--- stderr tail ---")
print(err_text[-1500:])
