import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

codex_path = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer"
log_path = os.path.join(cwd, "codex_pptx_csv.log")

cmd = [
    codex_path,
    "--dangerously-bypass-approvals-and-sandbox",
    "-C",
    cwd,
    "SPEC_pptx_csv.mdとTASKS_pptx_csv.mdを読んで全タスクを実装してください。修正対象はfile_parser.pyのみです。",
]

with open(log_path, "w", encoding="utf-8") as log:
    proc = subprocess.Popen(cmd, stdout=log, stderr=log, cwd=cwd, creationflags=0x00000008)

print(f"Codex起動: PID={proc.pid}")
print(f"ログ: {log_path}")
