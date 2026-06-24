import subprocess

SES_WORK = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
cmd = [
    "powershell",
    "-NoProfile",
    "-Command",
    f"$t = Get-ScheduledTask -TaskName SES_MatchingV3; "
    f'$t.Actions[0].WorkingDirectory = "{SES_WORK}"; '
    f"Set-ScheduledTask -TaskName SES_MatchingV3 -Action $t.Actions",
]
result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
print("returncode:", result.returncode)
print(result.stdout[:200])
print(result.stderr[:200])
