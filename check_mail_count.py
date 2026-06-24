# -*- coding: utf-8 -*-
import imaplib
import ssl
import sys
from datetime import datetime

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

IMAP_SERVER = "mail65.onamae.ne.jp"
IMAP_PORT = 993

accounts = [
    {
        "user": env.get("OUTLOOK_EMAIL", "sessales@terra-ltd.co.jp"),
        "password": env.get("OUTLOOK_PASSWORD", ""),
        "label": "sessales",
    },
    {
        "user": env.get("MATSUNO_EMAIL", "r-matsuno@terra-ltd.co.jp"),
        "password": env.get("MATSUNO_PASSWORD", ""),
        "label": "matsuno",
    },
    {
        "user": env.get("OKAMOTO_EMAIL", "r-okamoto@terra-ltd.co.jp"),
        "password": env.get("OKAMOTO_PASSWORD", ""),
        "label": "okamoto",
    },
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

today_str = datetime.now().strftime("%d-%b-%Y")
yesterday_str = (datetime.now() - __import__("datetime").timedelta(days=1)).strftime("%d-%b-%Y")

for acc in accounts:
    if not acc["password"]:
        print(f"{acc['label']}: パスワード未設定")
        continue
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=ctx)
        mail.login(acc["user"], acc["password"])
        mail.select("INBOX")

        # 今日来たメール
        _, today_msgs = mail.search(None, f"SINCE {today_str}")
        today_ids = today_msgs[0].split() if today_msgs[0] else []

        # 昨日来たメール
        _, yest_msgs = mail.search(None, f"SINCE {yesterday_str}")
        yest_ids = yest_msgs[0].split() if yest_msgs[0] else []

        # 全件
        _, all_msgs = mail.search(None, "ALL")
        all_ids = all_msgs[0].split() if all_msgs[0] else []

        print(f"\n{acc['label']} ({acc['user']}):")
        print(f"  全件数: {len(all_ids)}件")
        print(f"  今日以降: {len(today_ids)}件")
        print(f"  昨日以降: {len(yest_ids)}件")
        print(f"  → 昨日だけ: {len(yest_ids) - len(today_ids)}件")

        mail.logout()
    except Exception as e:
        print(f"{acc['label']}: エラー {e}")

# processed_ids件数も確認
import json
from pathlib import Path

pid_path = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\processed_ids.json")
if pid_path.exists():
    pids = json.loads(pid_path.read_text(encoding="utf-8"))
    print(f"\n処理済みID数: {len(pids)}件")
