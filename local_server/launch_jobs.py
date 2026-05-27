import urllib.request, urllib.error, json, sys

TOKEN = "jobz-terra-2026"
BASE = "http://127.0.0.1:8765"

def run_bg(cmd, cwd, job_id):
    payload = json.dumps({"cmd": cmd, "cwd": cwd, "job_id": job_id}).encode()
    req = urllib.request.Request(f"{BASE}/run_bg", data=payload,
        headers={"Content-Type": "application/json", "X-Auth-Token": TOKEN}, method="POST")
    r = urllib.request.urlopen(req, timeout=10)
    print(r.read().decode())

SES = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# freee invoice テスト実行
run_bg("python freee\\freee_invoice_v2.py", SES, "freee_test_001")

# cleanup_v2 実行
run_bg("python cleanup_v2.py", SES, "cleanup_001")
