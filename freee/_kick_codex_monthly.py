import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import requests

CODEX = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
INSTRUCTION = (
    "Read freee/FIX_monthly.md carefully and implement a NEW file "
    "freee/freee_invoice_monthly.py strictly following that spec. "
    "Reference freee/_proposal2.py and freee/freee_invoice_v3.py for the existing logic and "
    "generalize it; do NOT modify those two files. "
    "The target work-month must be auto-derived as the previous month of date.today(). "
    "Use column index 15 (TERRA request amount) as the source of truth for TERRA amounts; "
    "skip any row whose col15 contains the no-billing text. "
    "Withholding tax must be true only for TERRA (partner kabushikigaisha TERRA); FT and GL false. "
    "Saito should be a flat 15000 from June onward (handled by the P default / col15 rule). "
    "Default mode is dry-run (print payloads, no POST); only POST when --execute is passed. "
    "After writing the file, run py_compile on it, then run it once with NO arguments (dry-run) "
    "and confirm it prints the target month, close date, billing_date, subject, and the per-group "
    "payloads without errors. Absolutely never POST in this verification run."
)
cmd = '"{0}" exec "{1}" --dangerously-bypass-approvals-and-sandbox'.format(CODEX, INSTRUCTION)

resp = requests.post(
    "http://127.0.0.1:8765/run_bg",
    headers={"X-Auth-Token": "jobz-terra-2026"},
    json={
        "cmd": cmd,
        "cwd": r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
        "job_id": "codex_monthly",
    },
    timeout=30,
)
print("POST /run_bg ->", resp.status_code)
print(resp.text)
