import os
import subprocess

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_pipeline_v1.log"
cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1"

os.makedirs(os.path.dirname(log_path), exist_ok=True)

with open(log_path, "w", encoding="utf-8") as f:
    proc = subprocess.Popen(
        [
            "codex",
            "exec",
            "CLAUDE.mdとSPEC.mdを読んでTASKS.mdの1〜19番をPhase A→B→C→Dの順番で実装してください",
            "--dangerously-bypass-approvals-and-sandbox",
        ],
        cwd=cwd,
        stdout=f,
        stderr=f,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )
    print(f"Codex PID: {proc.pid}", flush=True)
    print(f"Log: {log_path}", flush=True)
