import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("task_auto_runner/_bootstrap_prompt.txt", encoding="utf-8") as f:
    prompt_text = f.read()

ses_work = os.getcwd()

# claude.cmd のフルパスを使う
claude_path = r"C:\Users\ma_py\AppData\Roaming\npm\claude.cmd"

cmd = [
    claude_path,
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

result = subprocess.run(
    cmd,
    capture_output=True,
    cwd=ses_work,
    timeout=1500,
    shell=False,
)

duration = time.time() - start
print(f"[{time.strftime('%H:%M:%S')}] 完了, duration={duration:.1f}s, exit={result.returncode}")

out_text = result.stdout.decode("utf-8", errors="replace")
err_text = result.stderr.decode("utf-8", errors="replace")

with open("task_auto_runner/logs/bootstrap_run.log", "w", encoding="utf-8") as f:
    f.write(out_text)
with open("task_auto_runner/logs/bootstrap_err.log", "w", encoding="utf-8") as f:
    f.write(err_text)

print(f"stdout: {len(out_text)} chars / stderr: {len(err_text)} chars")
print("\n--- stdout tail ---")
print(out_text[-3000:])
print("\n--- stderr tail ---")
print(err_text[-1000:])
