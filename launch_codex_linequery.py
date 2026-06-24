import os
import subprocess

ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
codex = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
log_path = os.path.join(ses, "codex_linequery_bugfix.log")

prompt = "SPEC_linequery_bugfix.md\u3068TASKS_linequery_bugfix.md\u3092\u8aad\u3093\u3067line_query.py\u306e\u30d0\u30b0\u3092\u4fee\u6b63\u3057\u3066TASKS_linequery_bugfix.md\u3092\u66f4\u65b0\u3057\u3066\u304f\u3060\u3055\u3044"

with open(log_path, "w", encoding="utf-8") as log_f:
    proc = subprocess.Popen(
        [codex, "exec", prompt, "--dangerously-bypass-approvals-and-sandbox"],
        cwd=ses,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        creationflags=0x08000000,  # CREATE_NO_WINDOW
    )

print(f"Codex PID: {proc.pid}")
print(f"Log: {log_path}")
