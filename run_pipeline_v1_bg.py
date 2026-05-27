import subprocess, os

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\pipeline_v1_run.log"
cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1"
codex_cmd = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"

with open(log_path, "w", encoding="utf-8") as f:
    proc = subprocess.Popen(
        [codex_cmd, "exec",
         "CLAUDE.mdとSPEC.mdを読んでTASKS.mdの1〜19番をPhase A→B→C→Dの順番で実装してください",
         "--dangerously-bypass-approvals-and-sandbox"],
        cwd=cwd,
        stdout=f,
        stderr=f,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    )
    print(f"PID: {proc.pid}", flush=True)
    print(f"Log: {log_path}", flush=True)
