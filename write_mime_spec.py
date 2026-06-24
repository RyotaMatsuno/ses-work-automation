content_spec = """# SPEC.md - ses-mail MIME添付対応

最終更新: 2026-05-26

## 概要
提案メール送信時にスキルシート（Excel/PDF）を添付できるようにする。
所属から送られてきたスプレッドシートをExcelとしてダウンロードして添付する。

## 対象ファイル
- ses_work/mail_mcp/mail_server.py（添付送信機能を追加）

## 仕様

### 添付付きメール送信エンドポイント（mail_server.pyに追加）
既存の `send_email` 関数に `attachments` パラメータを追加：
```python
def send_email(account, to, subject, body, attachments=None):
    # attachments: list of {"filename": "sample.xlsx", "data": base64_str, "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
```

### smtplibでのMIMEMultipart実装
```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64

msg = MIMEMultipart()
# 本文
msg.attach(MIMEText(body, 'plain', 'utf-8'))
# 添付
for att in (attachments or []):
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(base64.b64decode(att["data"]))
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{att["filename"]}"')
    msg.attach(part)
```

## 完了条件
1. py_compile mail_mcp/mail_server.py → エラーなし
2. 既存の添付なし送信が引き続き動作すること
"""

content_tasks = """# TASKS.md - ses-mail MIME添付対応

- [ ] 1. mail_mcp/mail_server.pyの send_email 関数に attachments パラメータを追加
- [ ] 2. MIMEMultipartでbase64デコード→添付するロジックを実装
- [ ] 3. py_compile mail_mcp/mail_server.py → エラーなし確認
- [ ] 4. 既存のsend_email呼び出しが動作すること（attachments=Noneのデフォルト動作確認）
"""

import os

os.makedirs(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_mime_spec", exist_ok=True)

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_mime_spec\SPEC.md", "w", encoding="utf-8") as f:
    f.write(content_spec)
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_mime_spec\TASKS.md", "w", encoding="utf-8") as f:
    f.write(content_tasks)
print("MIME添付 SPEC/TASKS 作成完了")
