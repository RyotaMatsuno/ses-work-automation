
import requests

# RailwayのSMTP直接テスト用エンドポイントはないので
# ローカルから直接SMTPテストする（同じ設定で確認）
import smtplib, ssl
from email.mime.text import MIMEText
from email.header import Header

accounts = {
    "matsuno": {"user": "r-matsuno@terra-ltd.co.jp", "pw": "N88[uR5:Ro!]"},
    "okamoto": {"user": "r-okamoto@terra-ltd.co.jp", "pw": "Egk:8gB3dr"},
    "sessales": {"user": "sessales@terra-ltd.co.jp", "pw": "te!rra!884568"},
}

# 松野アドレスでテスト送信（松野宛に）
acc = accounts["matsuno"]
to_addr = "r-matsuno@terra-ltd.co.jp"
subject = "【v12テスト】Railway SMTP送信確認"
body = "このメールはv12（Railway内SMTP直接送信）のテストです。\n受信できれば送信経路は正常です。"

try:
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = acc['user']
    msg['To'] = to_addr
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL('mail65.onamae.ne.jp', 465, context=ctx) as s:
        s.login(acc['user'], acc['pw'])
        s.sendmail(acc['user'], [to_addr], msg.as_bytes())
    print("SENT OK: matsuno -> matsuno")
except Exception as e:
    print(f"ERROR: {e}")
