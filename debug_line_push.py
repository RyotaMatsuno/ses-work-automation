from dotenv import dotenv_values
import requests

env = dotenv_values(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')
matsuno_token = env.get('LINE_CHANNEL_ACCESS_TOKEN','')
matsuno_uid = env.get('MATSUNO_LINE_USER_ID','')
print('MATSUNO_UID:', matsuno_uid)
print('TOKEN_PREFIX:', matsuno_token[:40]+'...')

res = requests.post(
    'https://api.line.me/v2/bot/message/push',
    headers={'Authorization': f'Bearer {matsuno_token}', 'Content-Type': 'application/json'},
    json={'to': matsuno_uid, 'messages': [{'type': 'text', 'text': 'テスト送信'}]}
)
print('status:', res.status_code, res.text[:300])
