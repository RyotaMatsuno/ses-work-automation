"""
Windowsタスクスケジューラにマッチング自動実行を登録する
毎朝8:00: matching_v2.py → notify_line.py
"""
import subprocess

bat_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\run_matching_and_notify.bat"

cmd = [
    'schtasks', '/create',
    '/tn', 'SES_MatchingAndNotify',
    '/tr', bat_path,
    '/sc', 'DAILY',
    '/st', '08:00',
    '/f',  # 上書き
    '/ru', 'SYSTEM'
]

result = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("RC:", result.returncode)
