import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

CODEX = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
CWD = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
LOG = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_integration\codex_run.log"

prompt = (
    "pipeline_integration/CLAUDE.md と pipeline_integration/SPEC.md を読んで、"
    "pipeline_integration/TASKS.md の順番で全タスクを実装してください。"
    "完了したTASKSのチェックボックスを埋めてください。"
)

with open(LOG, "w", encoding="utf-8") as lf:
    proc = subprocess.Popen(
        [CODEX, "exec", prompt, "--dangerously-bypass-approvals-and-sandbox", "-C", CWD], stdout=lf, stderr=lf, cwd=CWD
    )

print(f"Codex起動 PID: {proc.pid}", flush=True)
print(f"ログ: {LOG}", flush=True)
print("バックグラウンド実行中...", flush=True)
