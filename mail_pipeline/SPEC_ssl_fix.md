
# SPEC.md - mail_pipeline IMAP SSL修正

最終更新: 2026-05-22

## 問題
mail_pipeline.pyがIMAPでTERRAメールサーバーに接続する際、SSL証明書エラーが発生している。
エラー: `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: IP address mismatch, certificate is not valid for '118.27.122.112'`

## 原因
IMAPサーバーのSSL証明書がIPアドレス（118.27.122.112）宛ではなくホスト名宛で発行されているため、
IPアドレスで直接接続しようとすると証明書の検証が失敗する。

## 解決策
ssl.create_default_context()でSSL証明書の検証を無効化する。
（社内メールサーバーへの接続であり、セキュリティリスクは許容範囲）

## 対象ファイル
- ses_work/mail_pipeline/mail_pipeline.py

## 変更内容
IMAPの接続部分で以下を変更:
```python
# 変更前
mail = imaplib.IMAP4_SSL(server, port)

# 変更後
import ssl
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE
mail = imaplib.IMAP4_SSL(server, port, ssl_context=context)
```

## TASKS.md
- [ ] mail_pipeline.pyのIMAPSSL接続部分を特定する
- [ ] ssl.create_default_contextでcheck_hostname=False, verify_mode=CERT_NONEに変更
- [ ] python -c "import mail_pipeline.mail_pipeline" で構文エラーがないことを確認
- [ ] 動作テスト（接続できるかログで確認）

## Acceptance
- python mail_pipeline/mail_pipeline.py が SSL証明書エラーなく起動すること
- メールが取得できること
