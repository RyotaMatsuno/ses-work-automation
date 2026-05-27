import sys, requests, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values
cfg = dotenv_values(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')

# OpenAI: gpt-4o-miniで生成テスト
r = requests.post(
    'https://api.openai.com/v1/chat/completions',
    headers={'Authorization': f'Bearer {cfg["OPENAI_API_KEY"]}', 'Content-Type': 'application/json'},
    json={'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': '「稼働中」と一言だけ答えてください'}], 'max_tokens': 10},
    timeout=20
)
print('OpenAI生成:', r.status_code)
if r.status_code == 200:
    print('応答:', r.json()['choices'][0]['message']['content'])
else:
    print('Error:', r.json().get('error',{}).get('message','')[:200])

# Gemini: 30秒待ってリトライ
print('Gemini 30秒待機中...')
time.sleep(30)
from dotenv import dotenv_values
key = cfg["GEMINI_API_KEY"]
r2 = requests.post(
    f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}',
    json={'contents': [{'parts': [{'text': '「稼働中」と一言だけ答えてください'}]}]},
    timeout=15
)
print('Gemini生成:', r2.status_code)
if r2.status_code == 200:
    print('応答:', r2.json()['candidates'][0]['content']['parts'][0]['text'])
else:
    print('Error:', r2.json().get('error',{}).get('message','')[:200])
