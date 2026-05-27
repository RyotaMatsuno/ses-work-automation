
import subprocess, sys, os

codex_dir = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2"
cmd = 'codex exec "SPEC.mdとTASKS.mdを読んで、TASKS.mdに記載された全タスクを順番に実装してください。smoke testまで完走させてください。"'

print(f"Codex起動: {cmd}")
print(f"作業dir: {codex_dir}")

# バックグラウンドで起動（非ブロッキング）
proc = subprocess.Popen(
    cmd,
    shell=True,
    cwd=codex_dir,
    stdout=open(os.path.join(codex_dir, 'codex_output.log'), 'w', encoding='utf-8'),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
)
print(f"PID: {proc.pid}")
print("バックグラウンドで実行中。codex_output.logを確認してください。")
