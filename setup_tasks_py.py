import subprocess

tasks = [
    (
        "SES_Outlook_9h",
        "py",
        "C:\\Users\\ma_py\\OneDrive\\\u30c7\u30b9\u30af\u30c8\u30c3\u30d7\\ses_work\\outlook\\outlook_to_notion.py",
        "daily",
        "09:00",
    ),
    (
        "SES_Outlook_13h",
        "py",
        "C:\\Users\\ma_py\\OneDrive\\\u30c7\u30b9\u30af\u30c8\u30c3\u30d7\\ses_work\\outlook\\outlook_to_notion.py",
        "daily",
        "13:00",
    ),
    (
        "SES_Outlook_18h",
        "py",
        "C:\\Users\\ma_py\\OneDrive\\\u30c7\u30b9\u30af\u30c8\u30c3\u30d7\\ses_work\\outlook\\outlook_to_notion.py",
        "daily",
        "18:00",
    ),
]

for name, cmd, script, sc, st in tasks:
    r = subprocess.run(
        ["schtasks", "/create", "/tn", name, "/tr", f'{cmd} "{script}"', "/sc", sc, "/st", st, "/f", "/rl", "highest"],
        capture_output=True,
        text=True,
    )
    if r.returncode == 0:
        print(f"OK: {name} ({st})")
    else:
        print(f"FAIL: {name} - {r.stderr.strip()}")

# Freee monthly
r = subprocess.run(
    [
        "schtasks",
        "/create",
        "/tn",
        "SES_Freee_Invoice",
        "/tr",
        'py "C:\\Users\\ma_py\\OneDrive\\\u30c7\u30b9\u30af\u30c8\u30c3\u30d7\\ses_work\\freee\\freee_invoice.py"',
        "/sc",
        "monthly",
        "/d",
        "25",
        "/st",
        "10:00",
        "/f",
        "/rl",
        "highest",
    ],
    capture_output=True,
    text=True,
)
if r.returncode == 0:
    print("OK: SES_Freee_Invoice (monthly 25th)")
else:
    print(f"FAIL: SES_Freee_Invoice - {r.stderr.strip()}")

print("\nDone!")
