import subprocess, sys
proc = subprocess.Popen(
    ["codex", "exec", "SPEC_notify_v2.mdを読んでnotify_line.pyを修正してください", "--cd", "matching_v2"],
    stdout=open("codex_notify_v2.log", "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    creationflags=0x00000008
)
print(f"PID: {proc.pid}")
