path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# register_project関数を抜き出して確認
start = content.find('def register_project')
end = content.find('\ndef ', start + 1)
print(content[start:end])
