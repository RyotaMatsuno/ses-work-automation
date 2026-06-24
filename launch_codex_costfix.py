import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 正しいパスを確認
base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline")
print(f"存在確認: {base.exists()}")

codex = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
log_path = base / "codex_costfix.log"

cmd = (
    f'"{codex}" exec '
    '"CLAUDE_costfix.md と SPEC_costfix.md と TASKS_costfix.md を読んで、'
    "TASKS_costfix.md のタスクを順番に全て実装してください。"
    "完了したタスクは TASKS_costfix.md の [ ] を [x] に更新してください。"
    '最後に python -m py_compile mail_pipeline.py と DRY_RUN=1 python mail_pipeline.py を実行して結果を check_costfix_result.txt に書き出してください。" '
    f'-C "{base}" '
    "--dangerously-bypass-approvals-and-sandbox"
)

with open(log_path, "w", encoding="utf-8") as logf:
    proc = subprocess.Popen(
        cmd, shell=True, stdout=logf, stderr=logf, cwd=str(base), creationflags=subprocess.CREATE_NO_WINDOW
    )

print(f"Codex 起動 PID: {proc.pid}")
print(f"ログ: {log_path}")
