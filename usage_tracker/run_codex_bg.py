import requests

url = "http://127.0.0.1:8765/run_bg"
headers = {"X-Auth-Token": "jobz-terra-2026", "Content-Type": "application/json"}
payload = {
    "cmd": 'codex exec "CLAUDE.mdとSPEC.mdを読んでTASKS.mdの順番で全タスクを実装してください" --dangerously-bypass-approvals-and-sandbox',
    "cwd": r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
}

resp = requests.post(url, headers=headers, json=payload, timeout=10)
print(resp.status_code, flush=True)
print(resp.text, flush=True)
