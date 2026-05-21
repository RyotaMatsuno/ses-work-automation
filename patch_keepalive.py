import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old1 = 'import os, hmac, hashlib, base64, json, re, traceback'
new1 = 'import os, hmac, hashlib, base64, json, re, traceback, threading, time'

old2 = "if __name__ == '__main__':\n    port = int(os.environ.get('PORT', 5000))\n    app.run(host='0.0.0.0', port=port)"
new2 = """def _keepalive():
    time.sleep(60)
    url = os.environ.get('RENDER_EXTERNAL_URL', 'https://ses-work-automation.onrender.com')
    while True:
        try:
            requests.get(f'{url}/health', timeout=10)
            print('[keepalive] ping OK')
        except Exception as e:
            print(f'[keepalive] ping failed: {e}')
        time.sleep(600)

threading.Thread(target=_keepalive, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)"""

c1 = content.replace(old1, new1, 1)
c2 = c1.replace(old2, new2, 1)

print('keepalive added:', 'keepalive' in c2)
print('threading added:', 'threading' in c2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(c2)
print('write done')
