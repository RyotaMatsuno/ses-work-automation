"""
importer.py v3 - メール添付スキルシート自動取り込みシステム
パターンA（添付ファイル）/ B（スプレッドシート1人）/ C（スプレッドシート複数人）対応
スプレッドシートに複数案件がまとまっているパターン（案件版C）も対応
エントリポイント: python importer.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

LOG_PATH = Path(__file__).parent / "importer.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("importer")

PROCESSED_IDS_PATH = Path(__file__).parent / "processed_ids.json"


def load_processed_ids() -> dict:
    if not PROCESSED_IDS_PATH.exists():
        return {"sessales": [], "matsuno": [], "okamoto": []}
    try:
        with open(PROCESSED_IDS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"sessales": data, "matsuno": [], "okamoto": []}
            if isinstance(data, dict):
                for account in ["sessales", "matsuno", "okamoto"]:
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


def process_attachments(attachments: list, meta: dict) -> dict:
    """パターンA: 添付ファイルを人員/案件に分類してNotion登録"""
    from ai_extractor import classify_content, extract_projects
    from parsers.file_parser import parse_file
    from utils.notion_writer import register_project

    stats = {"success": 0, "skip": 0, "error": 0}

    for att in attachments:
        filename = att["filename"]
        ext = att["ext"]
        file_data = att["data"]

        text = parse_file(filename, ext, file_data)
        if not text or len(text.strip()) < 200:
            logger.warning(f"テキスト変換失敗または短すぎ: {filename} → スキップ")
            stats["error"] += 1
            continue

        content_type = classify_content(text)
        logger.info(f"コンテンツ判定: {filename} → {content_type}")

        if content_type == "engineer":
            logger.info(f"人員判定→スキップ（LINE手動登録のみ許可）: {filename}")
            stats["skip"] += 1
            continue
        elif content_type == "project":
            records = extract_projects(text, filename)
            if not records:
                logger.warning(f"案件情報抽出失敗: {filename} → スキップ")
                stats["error"] += 1
                continue
            for proj in records:
                result = register_project(proj, meta)
                stats["success" if result else "skip"] += 1
        else:
            logger.warning(f"判定不能のためスキップ: {filename}")
            stats["skip"] += 1

    return stats


def process_sheet_urls(sheet_urls: list, meta: dict) -> dict:
    """パターンB/C: 廃止。人員はLINE手動登録のみ。"""
    del meta  # 互換のため引数は維持
    logger.info(f"スプレッドシート人員登録パスは廃止済み。{len(sheet_urls)}件スキップ")
    return {"success": 0, "skip": len(sheet_urls), "error": 0}


def process_sheet_urls_projects(sheet_urls: list, meta: dict) -> dict:
    """案件版C: スプレッドシートURLから複数案件を抽出してNotion案件DBに登録"""
    from ai_extractor import extract_projects
    from sheet_fetcher import fetch_sheet_text
    from utils.notion_writer import register_project

    stats = {"success": 0, "skip": 0, "error": 0}

    for url in sheet_urls:
        logger.info(f"スプレッドシート取得（案件）: {url}")
        result = fetch_sheet_text(url)

        if result["status"] == "login_required":
            logger.info(f"ログイン必要のためスキップ: {url}")
            stats["skip"] += 1
            continue
        elif result["status"] == "error":
            logger.warning(f"スプレッドシート取得失敗: {url} - {result.get('error', '')}")
            stats["error"] += 1
            continue

        text = result.get("text", "")
        if not text or len(text.strip()) < 50:
            logger.warning(f"スプレッドシート内容が空または短すぎ: {url}")
            stats["error"] += 1
            continue

        projects = extract_projects(text, f"sheet:{url[:60]}")
        if not projects:
            logger.warning(f"案件情報抽出失敗（スプレッドシート）: {url}")
            stats["error"] += 1
            continue

        for proj in projects:
            reg_result = register_project(proj, meta)
            if reg_result:
                stats["success"] += 1
            else:
                stats["skip"] += 1

    return stats


def main() -> int:
    logger.info("===== インポート開始 =====")
    logger.info("ログファイル: %s", LOG_PATH.resolve())

    from mail_fetcher import fetch_new_emails
    from mail_fetcher import save_processed_id as mark_processed

    try:
        account = "all"
        if "--account" in sys.argv:
            account_index = sys.argv.index("--account")
            if len(sys.argv) <= account_index + 1:
                raise ValueError("--account には sessales/matsuno/okamoto/all を指定してください")
            account = sys.argv[account_index + 1]
        emails = fetch_new_emails(days_back=1, account=account)
    except ConnectionError as e:
        logger.error("IMAP接続失敗 → 中断: %s", e)
        return 1
    except Exception as e:
        logger.error("メール取得失敗 → 中断: %s", e)
        logger.error(traceback.format_exc())
        return 1

    if not emails:
        logger.info("新規メールなし → 終了")
        return 0

    logger.info("処理対象メール: %d件", len(emails))

    if os.environ.get("DRY_RUN") == "1":
        logger.info("DRY_RUN=1 のためメール取得確認のみで終了（Notion登録・処理済み記録なし）")
        return 0

    total_success = 0
    total_skip = 0
    total_error = 0
    mail_errors = 0

    for mail_index, mail_item in enumerate(emails, start=1):
        uid = mail_item["uid"]
        subject = mail_item["subject"]
        account_name = mail_item.get("account", "sessales")
        meta = {
            "subject": subject,
            "from": mail_item["from"],
            "date": mail_item["date"],
            "account": account_name,
        }

        logger.info(
            "--- [%d/%d] 処理開始: account=%s UID=%s 件名=%s ---",
            mail_index,
            len(emails),
            account_name,
            uid,
            subject[:50],
        )

        try:
            # パターンA: 添付ファイル → エンジニア登録
            if mail_item["attachments"]:
                logger.info("パターンA: 添付ファイル %d件", len(mail_item["attachments"]))
                stats = process_attachments(mail_item["attachments"], meta)
                total_success += stats["success"]
                total_skip += stats["skip"]
                total_error += stats["error"]

            # パターンB/C: スプレッドシートURL → エンジニア登録（複数人対応）
            if mail_item.get("sheet_urls"):
                logger.info("パターンB/C: スプレッドシートURL（人員） %d件", len(mail_item["sheet_urls"]))
                stats = process_sheet_urls(mail_item["sheet_urls"], meta)
                total_success += stats["success"]
                total_skip += stats["skip"]
                total_error += stats["error"]

            # 案件版C: スプレッドシートURL → 案件登録（複数案件対応）
            if mail_item.get("project_sheet_urls"):
                logger.info("案件版C: スプレッドシートURL（案件） %d件", len(mail_item["project_sheet_urls"]))
                stats = process_sheet_urls_projects(mail_item["project_sheet_urls"], meta)
                total_success += stats["success"]
                total_skip += stats["skip"]
                total_error += stats["error"]

            mark_processed(uid, account_name)
            logger.info("account=%s UID=%s 処理済み記録完了", account_name, uid)
        except Exception as e:
            mail_errors += 1
            logger.error(
                "[%d/%d] メール処理失敗: account=%s UID=%s 件名=%s error=%s",
                mail_index,
                len(emails),
                account_name,
                uid,
                subject[:50],
                e,
            )
            logger.error(traceback.format_exc())
            continue

    logger.info(
        "===== 完了 登録:%d スキップ:%d エラー:%d メール処理失敗:%d =====",
        total_success,
        total_skip,
        total_error,
        mail_errors,
    )
    return 1 if mail_errors else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        logger.critical("致命的エラー:\n%s", traceback.format_exc())
        raise SystemExit(1)
