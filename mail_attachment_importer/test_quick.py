"""
test_quick.py - 軽量統合テスト（最新10件上限）
"""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("quick_test")

BASE_DIR = Path(__file__).parent


def test_step1_imap():
    """IMAP接続＋最新10件のみ取得"""
    logger.info("=== Step1: IMAP接続テスト（最新10件） ===")
    import email as email_lib
    import imaplib
    import os
    import re
    import socket
    from email.header import decode_header

    from dotenv import load_dotenv

    load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

    pw = (
        os.environ.get("SESSALES_MAIL_PASSWORD")
        or os.environ.get("SESSALES_PASSWORD")
        or os.environ.get("OUTLOOK_PASSWORD")
        or ""
    )
    server = os.environ.get("OUTLOOK_IMAP_SERVER", "118.27.122.112")
    port = int(os.environ.get("OUTLOOK_IMAP_PORT", 993))
    email_addr = "sessales@terra-ltd.co.jp"

    SHEET_URL_PATTERN = re.compile(r'https://docs\.google\.com/spreadsheets/d/[A-Za-z0-9_\-]+[^\s\r\n"<>]*')
    SUPPORTED_EXTS = {".xlsx", ".xls", ".pdf", ".docx", ".doc"}

    def decode_str(value):
        if not value:
            return ""
        parts = decode_header(value)
        result = []
        for part, charset in parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(str(part))
        return "".join(result)

    socket.setdefaulttimeout(30)
    mail = imaplib.IMAP4_SSL(server, port)
    mail.login(email_addr, pw)
    logger.info("IMAP接続・ログインOK")

    mail.select("INBOX")
    _, data = mail.uid("search", None, "ALL")
    all_uids = data[0].split() if data[0] else []
    logger.info(f"INBOX総件数: {len(all_uids)}件")

    # 最新10件のみ
    target_uids = all_uids[-10:]
    logger.info(f"処理対象: 最新{len(target_uids)}件")

    results = []
    for uid_bytes in target_uids:
        uid = uid_bytes.decode()
        _, msg_data = mail.uid("fetch", uid_bytes, "(RFC822)")
        if not msg_data or not msg_data[0]:
            continue
        raw = msg_data[0][1]
        msg = email_lib.message_from_bytes(raw)
        subject = decode_str(msg.get("Subject", ""))
        from_ = decode_str(msg.get("From", ""))

        attachments = []
        body_text = ""
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", "") or "")  # Headerオブジェクトを文字列に変換
            if "attachment" in cd:
                fn_raw = part.get_filename()
                if fn_raw:
                    filename = decode_str(fn_raw)
                    ext = Path(filename).suffix.lower()
                    if ext in SUPPORTED_EXTS:
                        data_bytes = part.get_payload(decode=True)
                        if data_bytes:
                            attachments.append({"filename": filename, "ext": ext, "size": len(data_bytes)})
            elif ct == "text/plain" and not body_text:
                payload = part.get_payload(decode=True)
                if payload:
                    for enc in ["utf-8", "iso-2022-jp", "shift_jis", "euc-jp"]:
                        try:
                            body_text = payload.decode(enc)
                            break
                        except:
                            continue

        sheet_urls = list(set(SHEET_URL_PATTERN.findall(body_text)))
        results.append(
            {
                "uid": uid,
                "subject": subject[:60],
                "from": from_[:40],
                "attachments": attachments,
                "has_sheet_url": len(sheet_urls) > 0,
            }
        )
        logger.info(f"  UID={uid} 件名={subject[:40]} 添付={len(attachments)} URL={len(sheet_urls)}")

    mail.logout()
    logger.info("IMAP Step1 OK")
    return results


def test_step2_ai():
    """Claude API抽出テスト"""
    logger.info("=== Step2: Claude API抽出テスト ===")
    from ai_extractor import extract_engineers

    sample = "氏名: 山田花子\n経験年数: 3年\n希望単価: 55万円\n稼働可能: 来月\nスキル: Python, Django, PostgreSQL"
    result = extract_engineers(sample, "test.txt")
    if result:
        logger.info(f"Claude API OK: {json.dumps(result, ensure_ascii=False)}")
        return True
    logger.error("Claude API抽出失敗")
    return False


def test_step3_notion():
    """Notion重複チェックテスト"""
    logger.info("=== Step3: Notion重複チェックテスト ===")
    from notion_writer import check_duplicate

    exists = check_duplicate("QUICK_TEST_99999")
    logger.info(f"Notion重複チェックOK: 結果={exists}")
    return True


if __name__ == "__main__":
    logger.info("===== 軽量統合テスト開始 =====")
    emails = test_step1_imap()
    logger.info(f"取得完了: {len(emails)}件")
    if not test_step2_ai():
        sys.exit(1)
    test_step3_notion()
    logger.info("===== 軽量統合テスト完了 =====")
