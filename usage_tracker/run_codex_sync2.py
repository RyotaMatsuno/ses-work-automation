import subprocess

cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\codex_run2.log"

instruction = (
    "usage_tracker/CLAUDE.mdとusage_tracker/SPEC.mdを読んで"
    "usage_tracker/TASKS.mdの順番で全タスクを実装してください。"
    "実装ファイルはすべてusage_tracker/ディレクトリ内に作成すること。"
    "既存のwall_hitting.pyやSPEC.md等には一切触れないこと。"
)

cmd = f'codex exec "{instruction}" --dangerously-bypass-approvals-and-sandbox'

print("Codex starting (run2)...", flush=True)
result = subprocess.run(
    cmd,
    shell=True,
    cwd=cwd,
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace',
    timeout=290
)

output = result.stdout + result.stderr
with open(log_path, 'w', encoding='utf-8') as f:
    f.write(output)

print(f"returncode={result.returncode}", flush=True)
print(output[-3000:], flush=True)
