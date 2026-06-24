import subprocess

# cost_guardを30分おきに実行するタスクを登録
cmd = [
    "schtasks",
    "/Create",
    "/F",
    "/TN",
    "SES_CostGuard",
    "/TR",
    r"python C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cost_guard.py",
    "/SC",
    "MINUTE",
    "/MO",
    "30",
    "/ST",
    "00:00",
]

result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
print(f"returncode: {result.returncode}")
print(result.stdout)
print(result.stderr)
