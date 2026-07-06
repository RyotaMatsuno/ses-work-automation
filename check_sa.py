import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

KEY = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json'
with open(KEY, 'r') as f:
    data = json.load(f)
print(f"サービスアカウントメール: {data['client_email']}")
