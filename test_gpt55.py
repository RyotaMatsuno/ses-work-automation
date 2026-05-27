import sys, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values
cfg = dotenv_values(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')

# gpt-5.5で疎通確認
r = requests.post(
    'https://api.openai.com/v1/chat/completions',
    headers={'Authorization': f'Bearer {cfg["OPENAI_API_KEY"]}', 'Content-Type': 'application/json'},
    json={'model': 'gpt-5.5', 'messages': [{'role': 'user', 'content': '「稼働中」と一言だけ答えてください'}], 'max_tokens': 10},
    timeout=30
)
print('gpt-5.5:', r.status_code)
if r.status_code == 200:
    print('応答:', r.json()['choices'][0]['message']['content'])
else:
    print('Error:', r.json().get('error',{}).get('message','')[:200])
