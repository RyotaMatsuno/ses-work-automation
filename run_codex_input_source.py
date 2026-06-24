import subprocess

cmd = (
    "codex exec "
    '"SPEC_input_source.mdを読んでTASKS_input_source.mdの順番で全タスクを実装してください。'
    "credentialはconfig/.envからdotenv_valuesで読み込む。"
    "Notionプロパティが存在しない場合はエラーにせずスキップ。"
    'webhook_server.pyは既存処理を壊さないよう必要箇所のみ追記する。" '
    "--dangerously-bypass-approvals-and-sandbox"
)

proc = subprocess.Popen(
    cmd,
    shell=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    stdout=open("codex_input_source.log", "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
)
print(f"Codex PID: {proc.pid}", flush=True)
