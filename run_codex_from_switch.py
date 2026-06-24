import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CODEX = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_from_switch.log"

proc = subprocess.Popen(
    [
        CODEX,
        "exec",
        "SPEC.mdを読んでTASKS.mdの順番で実装してください。CLAUDE.mdの禁止事項を必ず守ること。対象ファイルはparent直下のmail_pipeline/mail_pipeline.pyです。",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\from_switch_spec",
    ],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\from_switch_spec",
    stdout=open(log_path, "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW,
)
print(f"Codex Fromスイッチ PID: {proc.pid}", flush=True)
