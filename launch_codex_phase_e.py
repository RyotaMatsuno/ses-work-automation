import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

codex = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3"
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_phase_e.log"

instruction = (
    "TASKS.mdのPhase Eを読んで、E1からE7を順番に実装してください。"
    "各タスク完了後にTASKS.mdの[ ]を[x]に更新してください。"
    "CLAUDE.mdとSPEC.mdも参照して文脈を把握してから作業を開始してください。"
)

with open(log, "w", encoding="utf-8") as lf:
    proc = subprocess.Popen(
        [codex, "exec", instruction, "--dangerously-bypass-approvals-and-sandbox"],
        cwd=cwd,
        stdout=lf,
        stderr=lf,
        creationflags=0x00000008,  # DETACHED_PROCESS
    )

print(f"Codex PID: {proc.pid}")
print(f"Log: {log}")
