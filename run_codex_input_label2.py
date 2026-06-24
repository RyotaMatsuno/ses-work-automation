import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CODEX = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_input_label.log"

# input_label_specディレクトリに移動してCodexを実行
proc = subprocess.Popen(
    [
        CODEX,
        "exec",
        "SPEC.mdを読んでTASKS.mdの順番で実装してください。CLAUDE.mdの禁止事項を必ず守ること。対象ファイルはses_work直下のmail_pipeline/mail_pipeline.py、line_webhook/webhook_server.py、matching_v2/notify_line.pyです。",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\input_label_spec",
    ],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\input_label_spec",
    stdout=open(log_path, "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW,
)
print(f"Codex 入力元ラベル v2 PID: {proc.pid}", flush=True)
