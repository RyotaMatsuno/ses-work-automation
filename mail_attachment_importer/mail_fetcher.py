"""
mail_fetcher.py v3 - メール取得モジュール
対象: sessales@terra-ltd.co.jp
タイムアウト対策済み・パターンA/B/C対応
"""
import imaplib
import email
import json
import logging
import os
import re
import socket
from email.header import decode_header
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

logger = logging.getLogger(__name__)

SUPPORTED_EXTS = {".xlsx", ".xls", ".pdf", ".docx", ".doc"}
PROCESSED_IDS_PATH = Path(__file__).parent / "processed_ids.json"
SHEET_URL_PATTERN = re.compile(r'https://docs\.google\.com/spreadsheets/d/[A-Za-z0-9_\-]+[^\s\r\n"<>]*')

# IMAP接続タイムアウト（秒）
IMAP_TIMEOUT = 30


def _get_account_config():
    """sessalesアカウント設定を.envから取得"""
    password = (
        os.environ.get("SESSALES_MAIL_PASSWORD")
        or os.environ.get("SESSALES_PASSWORD")
        or os.environ.get("OUTLOOK_PASSWORD")
        or ""
    )
    return {
        "email": os.environ.get("SESSALES_EMAIL", "sessales@terra-ltd.co.jp"),
        "password": password,
        "imap_server": os.environ.get("OUTLOOK_IMAP_SERVER", "118.27.122.112"),
        "imap_port": int(os.environ.get("OUTLOOK_IMAP_PORT", 993)),
    }


def _load_processed_ids() -> set:
    try:
        with open(PROCESSED_IDS_PATH, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_processed_id(uid: str):
    ids = _load_processed_ids()
    ids.add(uid)
    with open(PROCESSED_IDS_PATH, "w") as f:
        json.dump(list(ids), f)


def _decode_str(value) -> str:
    if value is None:
        return ""
    parts = decode_header(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(str(part))
    return "".join(result)


def _get_body_text(msg) -> str:
    """メール本文テキストを取得"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    for enc in ["utf-8", "iso-2022-jp", "shift_jis", "euc-jp"]:
                        try:
                            body = payload.decode(enc)
                            break
                        except Exception:
                            continue
                    break
            elif ct == "text/html" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    for enc in ["utf-8", "iso-2022-jp", "shift_jis", "euc-jp"]:
                        try:
                            body = payload.decode(enc)
                            break
                        except Exception:
                            continue
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            for enc in ["utf-8", "iso-2022-jp", "shift_jis", "euc-jp"]:
                try:
                    body = payload.decode(enc)
                    break
                except Exception:
                    continue
    return body


def fetch_new_emails(days_back: int = 30):
    """
    sessalesのINBOXから未処理メールを取得する。

    Args:
        days_back: 何日前までのメールを対象にするか（デフォルト30日）

    Returns:
        list of dict: [
            {
                "uid": str,
                "subject": str,
                "from": str,
                "date": str,
                "attachments": [{"filename": str, "ext": str, "data": bytes}],
                "sheet_urls": [str],
                "body_text": str,
            }
        ]
    """
    config = _get_account_config()
    if not config["password"]:
        raise ValueError("sessalesアカウントのパスワードが設定されていません")

    processed = _load_processed_ids()
    results = []

    # ソケットタイムアウト設定
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(IMAP_TIMEOUT)

    try:
        logger.info(f"IMAP接続開始: {config['imap_server']}:{config['imap_port']} (timeout={IMAP_TIMEOUT}s)")
        mail = imaplib.IMAP4_SSL(config["imap_server"], config["imap_port"])
        mail.login(config["email"], config["password"])
        logger.info(f"IMAP接続成功: {config['email']}")
    except socket.timeout:
        logger.error(f"IMAP接続タイムアウト ({IMAP_TIMEOUT}秒)")
        socket.setdefaulttimeout(old_timeout)
        raise ConnectionError(f"IMAP接続タイムアウト ({IMAP_TIMEOUT}秒): {config['imap_server']}")
    except Exception as e:
        socket.setdefaulttimeout(old_timeout)
        logger.error(f"IMAP接続失敗: {e}")
        raise

    try:
        mail.select("INBOX")

        # 日付絞り込み（直近N日）
        from datetime import datetime, timedelta
        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
        _, data = mail.uid("search", None, f'(SINCE "{since_date}")')
        all_uids = data[0].split() if data[0] else []
        logger.info(f"INBOX検索結果（直近{days_back}日）: {len(all_uids)}件")

        # 未処理のみ
        unprocessed = [u for u in all_uids if u.decode() not in processed]
        logger.info(f"未処理: {len(unprocessed)}件")

        for uid_bytes in unprocessed:
            uid = uid_bytes.decode()
            try:
                _, msg_data = mail.uid("fetch", uid_bytes, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                subject = _decode_str(msg.get("Subject", ""))
                from_ = _decode_str(msg.get("From", ""))
                date_ = msg.get("Date", "")

                attachments = []
                for part in msg.walk():
                    cd = str(part.get("Content-Disposition", "") or "")
                    if "attachment" not in cd:
                        continue
                    fn_raw = part.get_filename()
                    if not fn_raw:
                        continue
                    filename = _decode_str(fn_raw)
                    ext = Path(filename).suffix.lower()
                    if ext not in SUPPORTED_EXTS:
                        logger.debug(f"添付スキップ（対応外）: {filename}")
                        continue
                    file_data = part.get_payload(decode=True)
                    if not file_data:
                        continue
                    attachments.append({"filename": filename, "ext": ext, "data": file_data})
                    logger.info(f"添付取得: {filename} (UID={uid})")

                # 本文からスプレッドシートURL抽出
                body_text = _get_body_text(msg)
                sheet_urls = list(set(SHEET_URL_PATTERN.findall(body_text)))

                # 添付もURLもない → スキップ（UIDは記録しない）
                if not attachments and not sheet_urls:
                    logger.debug(f"スキップ（添付・URLなし）: UID={uid}")
                    continue

                results.append({
                    "uid": uid,
                    "subject": subject,
                    "from": from_,
                    "date": date_,
                    "attachments": attachments,
                    "sheet_urls": sheet_urls,
                    "body_text": body_text[:5000],
                })

            except Exception as e:
                logger.error(f"メール処理エラー (UID={uid}): {e}")
                continue

    finally:
        try:
            mail.logout()
        except Exception:
            pass
        socket.setdefaulttimeout(old_timeout)

    logger.info(f"取得完了: {len(results)}件（添付またはURL含むもの）")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    items = fetch_new_emails()
    print(f"\n取得件数: {len(items)}")
    for item in items[:5]:
        print(f"  [{item['uid']}] {item['subject'][:50]}")
        print(f"    添付: {[a['filename'] for a in item['attachments']]}")
        print(f"    URL: {item['sheet_urls']}")
