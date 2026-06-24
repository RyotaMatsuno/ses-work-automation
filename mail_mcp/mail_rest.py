# -*- coding: utf-8 -*-
"""
SES Mail REST CLI
jobz-command (localhost:8765) の /run 経由で呼び出す IMAP 操作 CLI。
標準出力に JSON を返す。常駐プロセス不要。

例:
  python mail_mcp/mail_rest.py fetch --account matsuno --limit 20
  python mail_mcp/mail_rest.py search --account matsuno --query "フラップ" --limit 10
  python mail_mcp/mail_rest.py mark_read --account matsuno --uid 12345
  python mail_mcp/mail_rest.py list_folders --account matsuno
"""

from __future__ import annotations

import argparse
import email
import imaplib
import json
import re
import ssl
import sys
from datetime import timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path

from dotenv import dotenv_values

try:
    from common.io_utils import setup_stdout

    setup_stdout()
except Exception:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "config" / ".env"
IMAP_TIMEOUT = 30
BODY_PREVIEW_LEN = 2000

ACCOUNT_NAMES = ("matsuno", "okamoto", "sessales")
DEFAULT_IMAP_HOST = "mail65.onamae.ne.jp"
DEFAULT_IMAP_PORT = 993

# command_server.py 互換（/mail/* エンドポイント）
MAIL_ENDPOINTS = {
    "/mail/search": "mail_search",
    "/mail/fetch": "mail_fetch",
    "/mail/send_draft": "mail_send_draft",
}


def _load_env() -> dict:
    if not ENV_PATH.exists():
        return {}
    return dotenv_values(ENV_PATH, encoding="utf-8")


def _password(env: dict, *keys: str) -> str:
    for key in keys:
        value = env.get(key)
        if value:
            return value
    return ""


def get_account_config(account_name: str) -> dict | None:
    """matsuno / okamoto / sessales の接続設定を .env から組み立てる。"""
    if account_name not in ACCOUNT_NAMES:
        return None

    env = _load_env()
    if account_name == "matsuno":
        password = _password(env, "MATSUNO_MAIL_PASSWORD", "MATSUNO_PASSWORD")
        return {
            "account": "matsuno",
            "email": env.get("MATSUNO_EMAIL", "r-matsuno@terra-ltd.co.jp"),
            "password": password,
            "imap_host": env.get("MATSUNO_IMAP_HOST", DEFAULT_IMAP_HOST),
            "imap_port": int(env.get("MATSUNO_IMAP_PORT") or DEFAULT_IMAP_PORT),
        }
    if account_name == "okamoto":
        password = _password(env, "OKAMOTO_MAIL_PASSWORD", "OKAMOTO_PASSWORD")
        return {
            "account": "okamoto",
            "email": env.get("OKAMOTO_EMAIL", "r-okamoto@terra-ltd.co.jp"),
            "password": password,
            "imap_host": env.get("OKAMOTO_IMAP_HOST", DEFAULT_IMAP_HOST),
            "imap_port": int(env.get("OKAMOTO_IMAP_PORT") or DEFAULT_IMAP_PORT),
        }

    password = _password(
        env,
        "SESSALES_MAIL_PASSWORD",
        "SESSALES_PASSWORD",
        "OUTLOOK_PASSWORD",
    )
    return {
        "account": "sessales",
        "email": env.get("SESSALES_EMAIL") or env.get("OUTLOOK_EMAIL", "sessales@terra-ltd.co.jp"),
        "password": password,
        "imap_host": env.get("OUTLOOK_IMAP_SERVER", DEFAULT_IMAP_HOST),
        "imap_port": int(env.get("OUTLOOK_IMAP_PORT") or DEFAULT_IMAP_PORT),
    }


def _ssl_context(host: str) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if host in ("mail65.onamae.ne.jp", "118.27.122.112"):
        # onamaeサーバー(mail65.onamae.ne.jp)は証明書検証が通らないため緩和
        # mail_server.py / mail_fetcher.py と同設定。内部呼び出し専用のため許容。
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _classify_imap_error(exc: Exception) -> tuple[str, str]:
    msg = str(exc)
    lower = msg.lower()
    if isinstance(exc, imaplib.IMAP4.error) or "authentication failed" in lower or "login" in lower:
        return "auth_failed", msg
    if "timeout" in lower or "timed out" in lower or "connection" in lower or "refused" in lower:
        return "connection_failed", msg
    return "imap_error", msg


def connect_imap(account: dict) -> imaplib.IMAP4_SSL:
    mail = imaplib.IMAP4_SSL(
        account["imap_host"],
        account["imap_port"],
        ssl_context=_ssl_context(account["imap_host"]),
    )
    if mail.sock:
        mail.sock.settimeout(IMAP_TIMEOUT)
    mail.login(account["email"], account["password"])
    return mail


def decode_header_value(raw: str) -> str:
    if not raw:
        return ""
    parts: list[str] = []
    for part, enc in decode_header(raw):
        if isinstance(part, bytes):
            parts.append(_decode_bytes(part, enc))
        else:
            parts.append(str(part))
    return "".join(parts)


def _decode_bytes(data: bytes, charset: str | None = None) -> str:
    if charset:
        try:
            return data.decode(charset, errors="replace")
        except (LookupError, UnicodeDecodeError):
            pass

    for enc in ("utf-8", "iso-2022-jp", "shift_jis", "cp932", "euc-jp", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue

    try:
        import chardet

        detected = chardet.detect(data)
        if detected.get("encoding"):
            return data.decode(detected["encoding"], errors="replace")
    except Exception:
        pass

    return data.decode("utf-8", errors="replace")


def decode_body_text(msg: email.message.Message) -> str:
    text_plain = ""
    text_html = ""

    if msg.is_multipart():
        for part in msg.walk():
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition.lower():
                continue
            content_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            decoded = _decode_bytes(payload, part.get_content_charset())
            if content_type == "text/plain" and not text_plain:
                text_plain = decoded
            elif content_type == "text/html" and not text_html:
                text_html = decoded
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            decoded = _decode_bytes(payload, msg.get_content_charset())
            if msg.get_content_type() == "text/html":
                text_html = decoded
            else:
                text_plain = decoded

    body = text_plain or _strip_html(text_html)
    return body[:BODY_PREVIEW_LEN]


def _strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _format_date(raw: str) -> str:
    if not raw:
        return ""
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return raw


def _message_has_attachment(msg: email.message.Message) -> bool:
    if msg.is_multipart():
        for part in msg.walk():
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition.lower():
                return True
            filename = part.get_filename()
            if filename and part.get_content_maintype() != "multipart":
                return True
    return False


def _is_read(flags_data: bytes | str | None) -> bool:
    if not flags_data:
        return False
    flags = flags_data.decode() if isinstance(flags_data, bytes) else str(flags_data)
    return "\\Seen" in flags


def _uid_search(mail: imaplib.IMAP4_SSL, criteria: str | list) -> list[bytes]:
    if isinstance(criteria, list):
        _, data = mail.uid("search", None, *criteria)
    else:
        _, data = mail.uid("search", None, criteria)
    if not data or not data[0]:
        return []
    return data[0].split()


def _fetch_message_record(
    mail: imaplib.IMAP4_SSL,
    uid: bytes,
    *,
    read_override: bool | None = None,
) -> dict:
    _, msg_data = mail.uid("fetch", uid, "(RFC822 FLAGS)")
    if not msg_data or not msg_data[0] or not isinstance(msg_data[0], tuple):
        raise ValueError(f"メール UID '{uid.decode()}' を取得できません")

    raw = msg_data[0][1]
    flags_blob = msg_data[0][0]
    msg = email.message_from_bytes(raw)
    read = _is_read(flags_blob) if read_override is None else read_override

    return {
        "uid": uid.decode() if isinstance(uid, bytes) else str(uid),
        "subject": decode_header_value(msg.get("Subject", "")),
        "from": decode_header_value(msg.get("From", "")),
        "to": decode_header_value(msg.get("To", "")),
        "date": _format_date(msg.get("Date", "")),
        "body_text": decode_body_text(msg),
        "has_attachment": _message_has_attachment(msg),
        "read": read,
    }


def action_fetch(account_name: str, folder: str = "INBOX", limit: int = 20) -> dict:
    account = get_account_config(account_name)
    if not account:
        return {"status": "error", "error": "unknown_account"}
    if not account["password"]:
        return {"status": "error", "error": "auth_failed", "detail": "password not configured"}

    mail = None
    try:
        mail = connect_imap(account)
        status, _ = mail.select(folder, readonly=True)
        if status != "OK":
            return {"status": "error", "error": "imap_error", "detail": f"cannot open folder: {folder}"}

        uids = _uid_search(mail, "UNSEEN")
        recent_uids = list(reversed(uids[-limit:] if len(uids) > limit else uids))

        messages = []
        for uid in recent_uids:
            try:
                messages.append(_fetch_message_record(mail, uid, read_override=False))
            except Exception as exc:
                return {"status": "error", "error": "imap_error", "detail": str(exc)}

        return {"status": "ok", "account": account_name, "folder": folder, "messages": messages}
    except Exception as exc:
        code, detail = _classify_imap_error(exc)
        return {"status": "error", "error": code, "detail": detail}
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


def action_search(
    account_name: str,
    query: str,
    folder: str = "INBOX",
    limit: int = 10,
) -> dict:
    account = get_account_config(account_name)
    if not account:
        return {"status": "error", "error": "unknown_account"}
    if not query:
        return {"status": "error", "error": "invalid_request", "detail": "query is required"}
    if not account["password"]:
        return {"status": "error", "error": "auth_failed", "detail": "password not configured"}

    mail = None
    try:
        mail = connect_imap(account)
        status, _ = mail.select(folder, readonly=True)
        if status != "OK":
            return {"status": "error", "error": "imap_error", "detail": f"cannot open folder: {folder}"}

        uids: list[bytes] = []
        for criteria in (
            ["TEXT", query],
            ["SUBJECT", query],
            ["BODY", query],
            ["OR", "SUBJECT", query, "BODY", query],
        ):
            try:
                uids = _uid_search(mail, criteria)
                if uids:
                    break
            except Exception:
                continue

        if not uids:
            uids = _uid_search(mail, "ALL")

        recent_uids = list(reversed(uids[-max(limit * 5, limit) :] if len(uids) > limit * 5 else uids))
        query_lower = query.casefold()
        messages = []

        for uid in recent_uids:
            try:
                record = _fetch_message_record(mail, uid)
            except Exception:
                continue
            haystack = " ".join(
                [
                    record.get("subject", ""),
                    record.get("from", ""),
                    record.get("to", ""),
                    record.get("body_text", ""),
                ]
            ).casefold()
            if query_lower in haystack:
                messages.append(record)
            if len(messages) >= limit:
                break

        return {
            "status": "ok",
            "account": account_name,
            "folder": folder,
            "query": query,
            "messages": messages,
        }
    except Exception as exc:
        code, detail = _classify_imap_error(exc)
        return {"status": "error", "error": code, "detail": detail}
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


def action_mark_read(account_name: str, uid: str, folder: str = "INBOX") -> dict:
    account = get_account_config(account_name)
    if not account:
        return {"status": "error", "error": "unknown_account"}
    if not uid:
        return {"status": "error", "error": "invalid_request", "detail": "uid is required"}
    if not account["password"]:
        return {"status": "error", "error": "auth_failed", "detail": "password not configured"}

    mail = None
    try:
        mail = connect_imap(account)
        status, _ = mail.select(folder)
        if status != "OK":
            return {"status": "error", "error": "imap_error", "detail": f"cannot open folder: {folder}"}

        store_status, response = mail.uid("store", uid.encode(), "+FLAGS", r"(\Seen)")
        if store_status != "OK":
            return {
                "status": "error",
                "error": "imap_error",
                "detail": f"mark_read failed: {response}",
            }

        return {"status": "ok", "account": account_name, "folder": folder, "uid": str(uid)}
    except Exception as exc:
        code, detail = _classify_imap_error(exc)
        return {"status": "error", "error": code, "detail": detail}
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


def action_list_folders(account_name: str) -> dict:
    account = get_account_config(account_name)
    if not account:
        return {"status": "error", "error": "unknown_account"}
    if not account["password"]:
        return {"status": "error", "error": "auth_failed", "detail": "password not configured"}

    mail = None
    try:
        mail = connect_imap(account)
        status, data = mail.list()
        if status != "OK":
            return {"status": "error", "error": "imap_error", "detail": "list folders failed"}

        folders: list[dict] = []
        for item in data or []:
            if not item:
                continue
            decoded = item.decode() if isinstance(item, bytes) else str(item)
            match = re.match(r'\((?P<flags>[^)]*)\)\s+"(?P<delimiter>[^"]*)"\s+(?P<name>.+)', decoded)
            if match:
                folders.append(
                    {
                        "name": match.group("name"),
                        "delimiter": match.group("delimiter"),
                        "flags": match.group("flags"),
                    }
                )
            else:
                folders.append({"name": decoded, "delimiter": "", "flags": ""})

        return {"status": "ok", "account": account_name, "folders": folders}
    except Exception as exc:
        code, detail = _classify_imap_error(exc)
        return {"status": "error", "error": code, "detail": detail}
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


def emit(result: dict) -> None:
    print(json.dumps(result, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SES Mail IMAP REST CLI")
    subparsers = parser.add_subparsers(dest="action", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="未読メール取得")
    fetch_parser.add_argument("--account", required=True, choices=ACCOUNT_NAMES)
    fetch_parser.add_argument("--limit", type=int, default=20)
    fetch_parser.add_argument("--folder", default="INBOX")

    search_parser = subparsers.add_parser("search", help="キーワード検索")
    search_parser.add_argument("--account", required=True, choices=ACCOUNT_NAMES)
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--limit", type=int, default=10)
    search_parser.add_argument("--folder", default="INBOX")

    mark_read_parser = subparsers.add_parser("mark_read", help="既読マーク")
    mark_read_parser.add_argument("--account", required=True, choices=ACCOUNT_NAMES)
    mark_read_parser.add_argument("--uid", required=True)
    mark_read_parser.add_argument("--folder", default="INBOX")

    list_folders_parser = subparsers.add_parser("list_folders", help="フォルダ一覧")
    list_folders_parser.add_argument("--account", required=True, choices=ACCOUNT_NAMES)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        emit({"status": "error", "error": "invalid_request", "detail": "invalid arguments"})
        return int(exc.code or 1)

    try:
        if args.action == "fetch":
            result = action_fetch(args.account, folder=args.folder, limit=args.limit)
        elif args.action == "search":
            result = action_search(
                args.account,
                query=args.query,
                folder=args.folder,
                limit=args.limit,
            )
        elif args.action == "mark_read":
            result = action_mark_read(args.account, uid=args.uid, folder=args.folder)
        elif args.action == "list_folders":
            result = action_list_folders(args.account)
        else:
            result = {"status": "error", "error": "invalid_request", "detail": f"unknown action: {args.action}"}
    except Exception as exc:
        result = {"status": "error", "error": "internal_error", "detail": str(exc)}

    emit(result)
    return 0 if result.get("status") == "ok" else 1


# ---------------------------------------------------------------------------
# command_server.py 互換レイヤー（/mail/* エンドポイント）
# ---------------------------------------------------------------------------


def _legacy_success(result: dict) -> dict:
    return {"success": True, **result}


def _legacy_failure(error: str) -> dict:
    return {"success": False, "error": error}


def _build_search_criteria(criteria) -> str | list:
    if criteria is None:
        return "ALL"
    if isinstance(criteria, str):
        return criteria
    if isinstance(criteria, list):
        return criteria
    if isinstance(criteria, dict):
        terms: list[str] = []
        if criteria.get("from"):
            terms.extend(["FROM", criteria["from"]])
        if criteria.get("subject"):
            terms.extend(["SUBJECT", criteria["subject"]])
        if criteria.get("since"):
            terms.extend(["SINCE", criteria["since"]])
        if criteria.get("before"):
            terms.extend(["BEFORE", criteria["before"]])
        if criteria.get("unseen"):
            terms.append("UNSEEN")
        if criteria.get("seen"):
            terms.append("SEEN")
        return terms if terms else "ALL"
    return "ALL"


def mail_search(req: dict) -> dict:
    account_name = req.get("account", "")
    if req.get("query"):
        result = action_search(
            account_name,
            query=req["query"],
            folder=req.get("folder", "INBOX"),
            limit=int(req.get("limit", 10)),
        )
        if result.get("status") != "ok":
            return _legacy_failure(result.get("detail") or result.get("error", "search failed"))
        messages = result.get("messages", [])
    else:
        account = get_account_config(account_name)
        if not account:
            return _legacy_failure(f"アカウント '{account_name}' が見つかりません")

        folder = req.get("folder", "INBOX")
        limit = int(req.get("limit", 10))
        criteria = _build_search_criteria(req.get("criteria", "ALL"))
        mail = None
        try:
            mail = connect_imap(account)
            status, _ = mail.select(folder, readonly=True)
            if status != "OK":
                return _legacy_failure(f"フォルダ '{folder}' を開けません")

            uids = _uid_search(mail, criteria)
            recent_uids = list(reversed(uids[-limit:] if len(uids) >= limit else uids))
            messages = []
            for uid in recent_uids:
                try:
                    messages.append(_fetch_message_record(mail, uid))
                except Exception as exc:
                    return _legacy_failure(str(exc))
        except Exception as exc:
            return _legacy_failure(str(exc))
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

    return _legacy_success(
        {
            "account": account_name,
            "folder": req.get("folder", "INBOX"),
            "count": len(messages),
            "emails": [
                {
                    "id": msg["uid"],
                    "subject": msg["subject"],
                    "from": msg["from"],
                    "to": msg["to"],
                    "date": msg["date"],
                }
                for msg in messages
            ],
        }
    )


def mail_fetch(req: dict) -> dict:
    account_name = req.get("account", "")
    message_id = req.get("message_id", "")
    if not message_id:
        return _legacy_failure("message_id is required")

    account = get_account_config(account_name)
    if not account:
        return _legacy_failure(f"アカウント '{account_name}' が見つかりません")

    mail = None
    try:
        mail = connect_imap(account)
        folder = req.get("folder", "INBOX")
        status, _ = mail.select(folder, readonly=True)
        if status != "OK":
            return _legacy_failure(f"フォルダ '{folder}' を開けません")

        record = _fetch_message_record(mail, message_id.encode())
        full_body = bool(req.get("full_body", True))
        body_text = record.get("body_text", "")
        if not full_body:
            body_text = body_text[:500]
        return _legacy_success(
            {
                "account": account_name,
                "folder": folder,
                "id": message_id,
                "subject": record["subject"],
                "from": record["from"],
                "to": record["to"],
                "date": record["date"],
                "body": {"text_plain": body_text, "text_html": ""},
            }
        )
    except Exception as exc:
        return _legacy_failure(str(exc))
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


def mail_send_draft(req: dict) -> dict:
    import time
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.utils import formatdate, make_msgid

    account_name = req.get("account", "")
    to_addr = req.get("to", "")
    subject = req.get("subject", "")
    body = req.get("body", "")
    cc_addr = req.get("cc", "")

    account = get_account_config(account_name)
    if not account:
        return _legacy_failure(f"アカウント '{account_name}' が見つかりません")
    if not to_addr:
        return _legacy_failure("to is required")

    mail = None
    try:
        msg = MIMEMultipart()
        msg["From"] = account["email"]
        msg["To"] = to_addr
        if cc_addr:
            msg["Cc"] = cc_addr
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()
        msg.attach(MIMEText(body, "plain", "utf-8"))

        mail = connect_imap(account)
        internal_date = imaplib.Time2Internaldate(time.time())
        status, response = mail.append("Drafts", "\\Draft", internal_date, msg.as_bytes())
        if status != "OK":
            return _legacy_failure(f"下書き保存失敗: {status} {response}")

        return _legacy_success(
            {
                "account": account_name,
                "from": account["email"],
                "to": to_addr,
                "subject": subject,
                "message": "下書きを保存しました",
            }
        )
    except Exception as exc:
        return _legacy_failure(str(exc))
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


def handle_mail_request(path: str, body: dict) -> tuple[int, dict]:
    handler_name = MAIL_ENDPOINTS.get(path)
    if not handler_name:
        return 404, {"success": False, "error": f"unknown mail endpoint: {path}"}

    handler = globals()[handler_name]
    result = handler(body)
    status = 200 if result.get("success") else 400
    return status, result


if __name__ == "__main__":
    raise SystemExit(main())
