
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values

config = dotenv_values(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')

# メール関連の設定を確認
keys = ['OUTLOOK_EMAIL', 'OUTLOOK_EMAIL2', 'OUTLOOK_EMAIL3', 'OUTLOOK_IMAP_SERVER', 'OUTLOOK_IMAP_PORT']
for k in keys:
    v = config.get(k, '未設定')
    if 'PASS' not in k:
        print(f'{k}: {v}')

# タスクスケジューラ設定も確認
import subprocess
result = subprocess.run(['schtasks', '/query', '/fo', 'LIST', '/v'], capture_output=True, text=True, encoding='utf-8', errors='replace')
lines = result.stdout.split('\n')
current_task = ''
for line in lines:
    if 'タスク名' in line or 'Task Name' in line:
        current_task = line
    if 'mail' in line.lower() or 'pipeline' in line.lower() or 'outlook' in line.lower():
        print(current_task)
        print(line)
