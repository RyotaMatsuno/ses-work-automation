import hmac, hashlib, base64, json, requests

secret = 'REDACTED-SECRET'
body = json.dumps({
    'destination': 'test',
    'events': [{
        'type': 'message',
        'message': {'type': 'text', 'id': '1', 'text': '田中太郎、Java/Python、経験5年、単価65万、即稼働可'},
        'timestamp': 1715676000000,
        'source': {'type': 'user', 'userId': 'U123test'},
        'replyToken': 'test-reply-token-12345',
        'mode': 'active'
    }]
}, ensure_ascii=False)
body_bytes = body.encode('utf-8')
sig = base64.b64encode(hmac.new(secret.encode(), body_bytes, hashlib.sha256).digest()).decode()
res = requests.post(
    'https://ses-work-automation-production.up.railway.app/webhook',
    headers={'Content-Type': 'application/json', 'X-Line-Signature': sig},
    data=body_bytes, timeout=30
)
print(f'status: {res.status_code}')
print(f'body: {res.text[:300]}')
