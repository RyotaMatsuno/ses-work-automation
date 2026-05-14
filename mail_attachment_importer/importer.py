"""
importer.py v2 - メール添付スキルシート自動取り込みシステム
パターンA（添付ファイル）/ B（スプレッドシート1人）/ C（スプレッドシート複数人）対応
エントリポイント: python importer.py
"""
import json
import logging
import sys
from pathlib import Path

# ログ設定
LOG_PATH = Path(__file__).parent / "importer.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("importer")

PROCESSED_IDS_PATH = Path(__file__).parent / "processed_ids.json"


def load_processed_ids() -> set:
    try:
        with open(PROCESSED_IDS_PATH, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_processed_id(uid: str):
    ids = load_processed_ids()
    ids.add(uid)
    with open(PROCESSED_IDS_PATH, "w") as f:
        json.dump(list(ids), f)


def process_attachments(attachments: list, meta: dict) -> dict:
    """パターンA: 添付ファイルからエンジニア情報を抽出してNotion登録"""
    from file_parser import parse_file
    from ai_extractor import extract_engineers
    from notion_writer import register_engineer

    stats = {"success": 0, "skip": 0, "error": 0}

    for att in attachments:
        filename = att["filename"]
        ext = att["ext"]
        file_data = att["data"]

        # テキスト変換
        text = parse_file(filename, ext, file_data)
        if not text:
            logger.warning(f"テキスト変換失敗: {filename} → スキップ")
            stats["error"] += 1
            continue

        # Claude APIで抽出
        engineers = extract_engineers(text, filename)
        if not engineers:
            logger.warning(f"エンジニア情報抽出失敗: {filename} → スキップ")
            stats["error"] += 1
            continue

        # Notion登録
        for eng in engineers:
            result = register_engineer(eng, meta)
            if result:
                stats["success"] += 1
            else:
                stats["skip"] += 1

    return stats


def process_sheet_urls(sheet_urls: list, meta: dict) -> dict:
    """パターンB/C: スプレッドシートURLからエンジニア情報を抽出してNotion登録"""
    from sheet_fetcher import fetch_sheet_text
    from ai_extractor import extract_engineers
    from notion_writer import register_engineer

    stats = {"success": 0, "skip": 0, "error": 0}

    for url in sheet_urls:
        logger.info(f"スプレッドシート取得: {url}")
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

        # Claude APIで抽出（パターンB: 1人 / C: 複数人 → extract_engineersが配列で返す）
        engineers = extract_engineers(text, f"sheet:{url[:60]}")
        if not engineers:
            logger.warning(f"エンジニア情報抽出失敗（スプレッドシート）: {url}")
            stats["error"] += 1
            continue

        # Notion登録
        for eng in engineers:
            result = register_engineer(eng, meta)
            if result:
                stats["success"] += 1
            else:
                stats["skip"] += 1

    return stats


def main():
    logger.info("===== インポート開始 =====")

    from mail_fetcher import fetch_new_emails, save_processed_id as mark_processed

    # 1. メール取得
    try:
        emails = fetch_new_emails(days_back=1)  # 毎日実行想定: 1日分のみ処理
    except ConnectionError as e:
        logger.error(f"IMAP接続失敗 → 中断: {e}")
        return
    except Exception as e:
        logger.error(f"メール取得失敗 → 中断: {e}")
        return

    if not emails:
        logger.info("新規メールなし → 終了")
        return

    logger.info(f"処理対象メール: {len(emails)}件")

    total_success = 0
    total_skip = 0
    total_error = 0

    for mail_item in emails:
        uid = mail_item["uid"]
        subject = mail_item["subject"]
        meta = {
            "subject": subject,
            "from": mail_item["from"],
            "date": mail_item["date"],
        }

        logger.info(f"--- 処理開始: UID={uid} 件名={subject[:50]} ---")
        uid_had_success = False

        # パターンA: 添付ファイル
        if mail_item["attachments"]:
            logger.info(f"パターンA: 添付ファイル {len(mail_item['attachments'])}件")
            stats = process_attachments(mail_item["attachments"], meta)
            total_success += stats["success"]
            total_skip += stats["skip"]
            total_error += stats["error"]
            if stats["success"] > 0:
                uid_had_success = True

        # パターンB/C: スプレッドシートURL
        if mail_item["sheet_urls"]:
            logger.info(f"パターンB/C: スプレッドシートURL {len(mail_item['sheet_urls'])}件")
            stats = process_sheet_urls(mail_item["sheet_urls"], meta)
            total_success += stats["success"]
            total_skip += stats["skip"]
            total_error += stats["error"]
            if stats["success"] > 0:
                uid_had_success = True

        # 処理済みUID記録
        # 成功 or 重複スキップがあればUID記録（再処理しない）
        # エラーのみの場合もUID記録する（同じメールで永遠にリトライし続けるのを防ぐ）
        mark_processed(uid)
        logger.info(f"UID={uid} 処理済み記録完了")

    logger.info(f"===== 完了 登録:{total_success} スキップ:{total_skip} エラー:{total_error} =====")


if __name__ == "__main__":
    main()
