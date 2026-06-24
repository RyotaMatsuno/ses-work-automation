import subprocess

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\skill_autofill_codex.log"
cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1"
codex_cmd = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"

with open(log_path, "w", encoding="utf-8") as f:
    proc = subprocess.Popen(
        [
            codex_cmd,
            "exec",
            "SPEC_skill_autofill.mdを読んで、skill_autofill.pyを新規作成し、pipeline.pyのrun_pipeline()にautofill_skillsの呼び出しを追加してください。",
            "--dangerously-bypass-approvals-and-sandbox",
        ],
        cwd=cwd,
        stdout=f,
        stderr=f,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )
    print(f"PID: {proc.pid}", flush=True)
