import email
import imaplib
import ssl
import sys
from email.header import decode_header

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def decode_str(s):
    if not s:
        return ""
    parts = decode_header(s)
    result = ""
    for part, charset in parts:
        if isinstance(part, bytes):
            result += part.decode(charset or "utf-8", errors="replace")
        else:
            result += str(part)
    return result


SKILL_SHEET_EXTENSIONS = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".xlsx", ".xls"}


def has_attachment(msg):
    for part in msg.walk():
        disposition = str(part.get("Content-Disposition", ""))
        filename_raw = part.get_filename()
        filename = decode_str(filename_raw) if filename_raw else ""
        if filename:
            import pathlib

            ext = pathlib.Path(filename).suffix.lower()
            if ext in SKILL_SHEET_EXTENSIONS or "attachment" in disposition:
                return True, filename
    return False, ""


# 共通アドレスから最新500件を本文ごと取得して添付有無を確認
mail = imaplib.IMAP4_SSL("mail65.onamae.ne.jp", 993, ssl_context=ctx)
mail.login(config["OUTLOOK_EMAIL"], config["OUTLOOK_PASSWORD"])
mail.select("INBOX")
status, messages = mail.search(None, "ALL")
all_ids = messages[0].split()
target = list(reversed(all_ids))[:500]
print("共通アドレス最新500件の添付調査中...")

with_attach = []
without_attach = 0

for i, mid in enumerate(target):
    try:
        status, msg_data = mail.fetch(mid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        subj = decode_str(msg.get("Subject", ""))
        frm = decode_str(msg.get("From", ""))
        has_att, fname = has_attachment(msg)
        if has_att:
            with_attach.append({"subject": subj[:70], "from": frm[:50], "file": fname})
        else:
            without_attach += 1
    except Exception:
        pass
    if (i + 1) % 100 == 0:
        print(f"  {i + 1}件完了...")

mail.logout()

total = len(target)
print(f"\n=== 添付ファイル調査結果（{total}件） ===")
print(f"添付あり: {len(with_attach)}件 ({len(with_attach) / total * 100:.1f}%)")
print(f"添付なし: {without_attach}件 ({without_attach / total * 100:.1f}%)")
print("\n添付ありメールサンプル（全件）:")
for m in with_attach:
    print(f"  FILE: {m['file']}")
    print(f"  SUBJ: {m['subject']}")
    print(f"  FROM: {m['from']}")
    print()
