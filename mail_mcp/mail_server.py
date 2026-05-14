#!/usr/bin/env python3
"""
SES Mail MCP Server
Claude Desktopからメール送信・受信確認ができるMCPサーバー
"""

import json
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import os
from datetime import datetime
import sys
import io

# Windows stdout/stdinをUTF-8に強制
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

ACCOUNTS = {
    "matsuno": {
        "email": "r-matsuno@terra-ltd.co.jp",
        "password": os.environ.get("MATSUNO_MAIL_PASSWORD", ""),
        "imap_server": "mail65.onamae.ne.jp",
        "imap_port": 993,
        "smtp_server": "mail65.onamae.ne.jp",
        "smtp_port": 465,
    },
    "okamoto": {
        "email": "r-okamoto@terra-ltd.co.jp",
        "password": os.environ.get("OKAMOTO_MAIL_PASSWORD", ""),
        "imap_server": "mail65.onamae.ne.jp",
        "imap_port": 993,
        "smtp_server": "mail65.onamae.ne.jp",
        "smtp_port": 465,
    },
    "sessales": {
        "email": "sessales@terra-ltd.co.jp",
        "password": os.environ.get("SESSALES_MAIL_PASSWORD", ""),
        "imap_server": "mail65.onamae.ne.jp",
        "imap_port": 993,
        "smtp_server": "mail65.onamae.ne.jp",
        "smtp_port": 465,
    }
}

def send_email(account_name: str, to: str, subject: str, body: str) -> dict:
    account = ACCOUNTS.get(account_name)
    if not account:
        return {"success": False, "error": f"アカウント '{account_name}' が見つかりません"}
    try:
        msg = MIMEMultipart()
        msg["From"] = account["email"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP_SSL(account["smtp_server"], account["smtp_port"]) as server:
            server.login(account["email"], account["password"])
            server.sendmail(account["email"], to, msg.as_string())
        return {
            "success": True,
            "message": f"送信完了: {to} へ「{subject}」を送信しました",
            "from": account["email"],
            "to": to,
            "subject": subject,
            "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_recent_emails(account_name: str, limit: int = 10) -> dict:
    account = ACCOUNTS.get(account_name)
    if not account:
        return {"success": False, "error": f"アカウント '{account_name}' が見つかりません"}
    try:
        mail = imaplib.IMAP4_SSL(account["imap_server"], account["imap_port"])
        mail.login(account["email"], account["password"])
        mail.select("INBOX")
        _, data = mail.search(None, "ALL")
        ids = data[0].split()
        recent_ids = ids[-limit:] if len(ids) >= limit else ids
        recent_ids = list(reversed(recent_ids))
        emails = []
        for msg_id in recent_ids:
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            subject = ""
            raw_subject = msg.get("Subject", "")
            for part, enc in decode_header(raw_subject):
                if isinstance(part, bytes):
                    subject += part.decode(enc or "utf-8", errors="ignore")
                else:
                    subject += part
            sender = msg.get("From", "")
            date = msg.get("Date", "")
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="ignore")[:500]
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")[:500]
            emails.append({
                "id": msg_id.decode(),
                "subject": subject,
                "from": sender,
                "date": date,
                "body_preview": body
            })
        mail.logout()
        return {"success": True, "emails": emails, "count": len(emails)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_request(request: dict) -> dict:
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ses-mail-mcp", "version": "1.0.0"}
            }
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "tools": [
                    {
                        "name": "send_email",
                        "description": "メールを送信する。松野または岡本のアカウントから送信可能。",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "account": {"type": "string", "description": "'matsuno'(松野アドレス) / 'okamoto'(岡本アドレス) / 'sessales'(TERRA共通)"},
                                "to": {"type": "string", "description": "送信先メールアドレス"},
                                "subject": {"type": "string", "description": "件名"},
                                "body": {"type": "string", "description": "本文"}
                            },
                            "required": ["account", "to", "subject", "body"]
                        }
                    },
                    {
                        "name": "get_recent_emails",
                        "description": "最新のメール一覧を取得する",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "account": {"type": "string", "description": "'matsuno'(松野アドレス) / 'okamoto'(岡本アドレス) / 'sessales'(TERRA共通)"},
                                "limit": {"type": "integer", "description": "取得件数（デフォルト10）", "default": 10}
                            },
                            "required": ["account"]
                        }
                    }
                ]
            }
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})
        if tool_name == "send_email":
            result = send_email(args["account"], args["to"], args["subject"], args["body"])
        elif tool_name == "get_recent_emails":
            result = get_recent_emails(args["account"], args.get("limit", 10))
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=True, indent=2)}]
            }
        }

    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    }


def main():
    # stderrにログ出力（デバッグ用）
    sys.stderr.write("ses-mail-mcp: starting...\n")
    sys.stderr.flush()
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            
            request = json.loads(line)
            method = request.get("method", "")
            req_id = request.get("id")
            
            # 通知メッセージ（idなし）は応答不要
            if req_id is None:
                sys.stderr.write(f"ses-mail-mcp: notification received: {method}\n")
                sys.stderr.flush()
                continue
            
            response = handle_request(request)
            out = json.dumps(response, ensure_ascii=True)
            sys.stdout.write(out + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            continue
        except Exception as e:
            sys.stderr.write(f"ses-mail-mcp: error: {e}\n")
            sys.stderr.flush()
            if 'req_id' in dir() and req_id is not None:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32700, "message": str(e)}
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    main()
