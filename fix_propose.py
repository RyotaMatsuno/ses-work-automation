import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\propose_pipeline\propose.py")
content = p.read_text(encoding="utf-8")

# build_message関数をMIMEText対応に書き換え
old = """def build_message(subject: str, body: str, from_email: str, to_email: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.set_content(body, subtype="plain", charset="utf-8")
    return msg"""

new = """def build_message(subject: str, body: str, from_email: str, to_email: str) -> MIMEText:
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    return msg"""

if old in content:
    content = content.replace(old, new)
    # importも修正
    content = content.replace(
        "from email.message import EmailMessage\nfrom email.utils import formatdate, make_msgid",
        "from email.header import Header\nfrom email.mime.text import MIMEText\nfrom email.utils import formatdate, make_msgid",
    )
    # 型ヒント修正
    content = content.replace(
        "def append_draft(from_email: str, password: str, msg: EmailMessage) -> None:",
        "def append_draft(from_email: str, password: str, msg: MIMEText) -> None:",
    )
    p.write_text(content, encoding="utf-8")
    print("修正完了")
else:
    print("NG: 対象関数見つからず")
    idx = content.find("def build_message")
    print(content[idx : idx + 300])
