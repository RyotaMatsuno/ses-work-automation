import sys, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values
cfg = dotenv_values(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')

r = requests.get(
    'https://api.openai.com/v1/models',
    headers={'Authorization': f'Bearer {cfg["OPENAI_API_KEY"]}'},
    timeout=15
)
models = [m['id'] for m in r.json()['data']]
# gpt-4系・o3系・最新系を抽出
latest = [m for m in models if any(x in m for x in ['gpt-4o', 'o3', 'o1', 'gpt-5', 'o4'])]
latest.sort()
for m in latest:
    print(m)
