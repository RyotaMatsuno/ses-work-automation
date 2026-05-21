
import re

path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py'
with open(path, 'r', encoding='utf-8-sig') as f:
    content = f.read()

# send_email_via_callback 関数の開始と終了を見つける
start_marker = 'def send_email_via_callback('
end_marker = '\ndef reply_message('

old_start = content.find(start_marker)
old_end = content.find(end_marker, old_start)

if old_start == -1:
    print("ERROR: send_email_via_callback not found")
    exit(1)
if old_end == -1:
    print("ERROR: end marker not found")
    exit(1)

print(f"Found: start={old_start}, end={old_end}")
print("--- OLD function (first 200 chars) ---")
print(content[old_start:old_start+200])

NEW_FUNC = '''def send_email_via_callback(account, to_addr, subject, body):
    import smtplib, ssl
    from email.mime.text import MIMEText
    from email.header import Header as EmailHeader

    accounts_cfg = {
        'matsuno': {'user': 'r-matsuno@terra-ltd.co.jp', 'pw': os.environ.get('MATSUNO_MAIL_PASSWORD', os.environ.get('SESSALES_MAIL_PASSWORD', ''))},
        'okamoto': {'user': 'r-okamoto@terra-ltd.co.jp', 'pw': os.environ.get('OKAMOTO_MAIL_PASSWORD', os.environ.get('SESSALES_MAIL_PASSWORD', ''))},
        'sessales': {'user': 'sessales@terra-ltd.co.jp', 'pw': os.environ.get('SESSALES_MAIL_PASSWORD', '')},
    }
    acc = accounts_cfg.get(account, accounts_cfg['sessales'])
    user, pw = acc['user'], acc['pw']
    if not pw:
        print(f"[send_email] ERROR: パスワード未設定 account={account}")
        return False
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = EmailHeader(subject, 'utf-8')
        msg['From'] = user
        msg['To'] = to_addr
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL('mail65.onamae.ne.jp', 465, context=ctx) as s:
            s.login(user, pw)
            s.sendmail(user, [to_addr], msg.as_bytes())
        print(f"[send_email] SENT OK to={to_addr} from={user}")
        return True
    except Exception as e:
        print(f"[send_email] ERROR: {e}")
        return False
'''

new_content = content[:old_start] + NEW_FUNC + content[old_end:]

# バックアップ
with open(path + '.bak', 'w', encoding='utf-8') as f:
    f.write(content)
print("Backup saved.")

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print("DONE: v12 patch applied.")

# 確認
with open(path, 'r', encoding='utf-8') as f:
    check = f.read()
idx = check.find('def send_email_via_callback(')
print("--- NEW function (first 300 chars) ---")
print(check[idx:idx+300])
