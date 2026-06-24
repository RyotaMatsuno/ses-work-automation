"""
mail_fetcher.py v3 - メール取得モジュール
対象: sessales / matsuno / okamoto
タイムアウト対策済み・パターンA/B/C対応
"""

import argparse
import email
import imaplib
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
ACCOUNT_NAMES = ("sessales", "matsuno", "okamoto")


def _get_account_config(account: str) -> dict:
    """指定アカウント設定を.envから取得"""
    prefix = account.upper()
    password = os.environ.get(f"{prefix}_PASSWORD") or ""
    if account == "sessales":
        password = os.environ.get("SESSALES_MAIL_PASSWORD") or password or os.environ.get("OUTLOOK_PASSWORD") or ""

    return {
        "account": account,
        "email": os.environ.get(f"{prefix}_EMAIL", "sessales@terra-ltd.co.jp" if account == "sessales" else ""),
        "password": password,
        "imap_server": (os.environ.get("IMAP_HOST") or os.environ.get("OUTLOOK_IMAP_SERVER") or "118.27.122.112"),
        "imap_port": int(os.environ.get("IMAP_PORT") or os.environ.get("OUTLOOK_IMAP_PORT") or 993),
    }


def _target_accounts(account: str) -> list:
    if account == "all":
        return list(ACCOUNT_NAMES)
    if account not in ACCOUNT_NAMES:
        raise ValueError("--account は sessales/matsuno/okamoto/all のいずれかを指定してください")
    return [account]


def load_processed_ids() -> dict:
    if not PROCESSED_IDS_PATH.exists():
        return {"sessales": [], "matsuno": [], "okamoto": []}
    try:
        with open(PROCESSED_IDS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"sessales": data, "matsuno": [], "okamoto": []}
            if isinstance(data, dict):
                for account in ACCOUNT_NAMES:
                    data.setdefault(account, [])
                return data
            raise ValueError("processed_ids.jsonの形式がlist/dictではありません")
    except Exception as e:
        logger.error(f"processed_ids読み込みエラー: {e}")
        raise
    return {"sessales": [], "matsuno": [], "okamoto": []}


def save_processed_id(uid: str, account: str = "sessales"):
    ids = load_processed_ids()
    if account not in ids:
        ids[account] = []
    if uid not in ids[account]:
        ids[account].append(uid)
    try:
        with open(PROCESSED_IDS_PATH, "w", encoding="utf-8") as f:
            json.dump(ids, f, ensure_ascii=False)
    except Exception as e:
        logger.error(f"processed_ids保存エラー: {e}")
        raise


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


def _fetch_new_emails_for_account(config: dict, days_back: int, processed_ids: list) -> list:
    """
    1アカウントのINBOXから未処理メールを取得する。

    Args:
        config: _get_account_config() の戻り値
        days_back: 何日前までのメールを対象にするか
        processed_ids: 対象アカウントの処理済みUID一覧

    Returns:
        list of dict: [
            {
                "uid": str,
                "subject": str,
                "from": str,
                "date": str,
                "account": str,
                "attachments": [{"filename": str, "ext": str, "data": bytes}],
                "sheet_urls": [str],
                "body_text": str,
            }
        ]
    """
    account = config["account"]
    results = []

    # ソケットタイムアウト設定
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(IMAP_TIMEOUT)

    try:
        logger.info(
            f"IMAP接続開始: account={account} {config['imap_server']}:{config['imap_port']} (timeout={IMAP_TIMEOUT}s)"
        )
        mail = imaplib.IMAP4_SSL(config["imap_server"], config["imap_port"])
        mail.login(config["email"], config["password"])
        logger.info(f"IMAP接続成功: account={account} {config['email']}")
    except socket.timeout:
        logger.error(f"IMAP接続タイムアウト: account={account} ({IMAP_TIMEOUT}秒)")
        socket.setdefaulttimeout(old_timeout)
        raise ConnectionError(f"IMAP接続タイムアウト ({IMAP_TIMEOUT}秒): {config['imap_server']}")
    except Exception as e:
        socket.setdefaulttimeout(old_timeout)
        logger.error(f"IMAP接続失敗: account={account} {e}")
        raise

    try:
        mail.select("INBOX")

        # 日付絞り込み（直近N日）
        from datetime import datetime, timedelta

        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
        _, data = mail.uid("search", None, f'(SINCE "{since_date}")')
        all_uids = data[0].split() if data[0] else []
        logger.info(f"INBOX検索結果 account={account}（直近{days_back}日）: {len(all_uids)}件")

        # 未処理のみ
        processed = set(str(uid) for uid in processed_ids)
        unprocessed = [u for u in all_uids if u.decode() not in processed]
        logger.info(f"未処理 account={account}: {len(unprocessed)}件")

        if os.environ.get("DRY_RUN") == "1":
            logger.info(f"DRY_RUN=1: account={account} はIMAP接続確認のみで本文取得をスキップ")
            return results

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
                    logger.debug(f"スキップ（添付・URLなし）: account={account} UID={uid}")
                    continue

                results.append(
                    {
                        "uid": uid,
                        "subject": subject,
                        "from": from_,
                        "date": date_,
                        "account": account,
                        "attachments": attachments,
                        "sheet_urls": sheet_urls,
                        "body_text": body_text[:5000],
                    }
                )

            except Exception as e:
                logger.error(f"メール処理エラー (account={account} UID={uid}): {e}")
                continue

    finally:
        try:
            mail.logout()
        except Exception:
            pass
        socket.setdefaulttimeout(old_timeout)

    logger.info(f"取得完了 account={account}: {len(results)}件（添付またはURL含むもの）")
    return results


def fetch_new_emails(days_back: int = 30, account: str = "all"):
    """
    指定アカウントのINBOXから未処理メールを取得する。

    Args:
        days_back: 何日前までのメールを対象にするか（デフォルト30日）
        account: sessales/matsuno/okamoto/all（デフォルトall）
    """
    processed_by_account = load_processed_ids()
    results = []

    for account_name in _target_accounts(account):
        config = _get_account_config(account_name)
        if not config["email"] or not config["password"]:
            message = f"{account_name}アカウントのメールアドレスまたはパスワードが設定されていません"
            if account == "all":
                logger.warning(f"{message} → スキップ")
                continue
            raise ValueError(message)

        account_results = _fetch_new_emails_for_account(
            config,
            days_back,
            processed_by_account.get(account_name, []),
        )
        results.extend(account_results)

    logger.info(f"全アカウント取得完了: {len(results)}件（添付またはURL含むもの）")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", choices=["sessales", "matsuno", "okamoto", "all"], default="all")
    parser.add_argument("--days-back", type=int, default=30)
    args = parser.parse_args()

    items = fetch_new_emails(days_back=args.days_back, account=args.account)
    print(f"\n取得件数: {len(items)}")
    for item in items[:5]:
        print(f"  [{item.get('account', 'sessales')}:{item['uid']}] {item['subject'][:50]}")
        print(f"    添付: {[a['filename'] for a in item['attachments']]}")
        print(f"    URL: {item['sheet_urls']}")
