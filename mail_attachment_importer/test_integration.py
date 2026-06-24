"""
test_integration.py - 統合テスト
全モジュールの接続確認 + 実際のメール1件で動作確認
"""

import json
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("integration_test")


def test_imap_connection():
    """Step 1: IMAP接続テスト"""
    logger.info("=== Step 1: IMAP接続テスト ===")
    from mail_fetcher import fetch_new_emails

    try:
        emails = fetch_new_emails(days_back=1)
        logger.info(f"IMAP接続OK。直近7日のメール: {len(emails)}件")
        for e in emails[:3]:
            logger.info(f"  [{e['uid']}] {e['subject'][:60]}")
            logger.info(f"    添付: {len(e['attachments'])}件, URL: {len(e['sheet_urls'])}件")
        return emails
    except Exception as e:
        logger.error(f"IMAP接続失敗: {e}")
        return None


def test_file_parser():
    """Step 2: ファイルパーサーテスト（ダミーデータ）"""
    logger.info("=== Step 2: ファイルパーサーテスト ===")
    from file_parser import parse_file

    # 簡易テスト: parse_file関数が存在し呼び出し可能か確認
    result = parse_file("dummy.txt", ".txt", b"")
    logger.info(f"parse_file呼び出しOK (未対応形式のテスト: result={result})")
    return True


def test_ai_extractor():
    """Step 3: Claude API抽出テスト"""
    logger.info("=== Step 3: Claude API抽出テスト ===")
    from ai_extractor import extract_engineers

    sample = """
氏名: 田中太郎
経験年数: 5年
希望単価: 65万円
稼働可能: 即日
スキル: Java, Spring, Oracle, Linux, AWS
"""
    result = extract_engineers(sample, "test_sample.txt")
    if result:
        logger.info(f"Claude API OK。抽出結果: {json.dumps(result, ensure_ascii=False)}")
        return True
    else:
        logger.error("Claude API抽出失敗")
        return False


def test_notion_writer():
    """Step 4: Notion重複チェックテスト（登録はしない）"""
    logger.info("=== Step 4: Notion重複チェックテスト ===")
    from notion_writer import check_duplicate

    # 存在しないであろう名前で確認
    exists = check_duplicate("テスト統合テスト12345")
    logger.info(f"Notion重複チェックOK。'テスト統合テスト12345'の重複: {exists}")
    return True


def test_full_pipeline(emails):
    """Step 5: フルパイプラインテスト（添付ありメール1件を実際に処理）"""
    logger.info("=== Step 5: フルパイプラインテスト ===")

    if not emails:
        logger.info("処理対象メールなし → スキップ")
        return True

    # 添付ファイルがある最初のメールで試す
    target = None
    for e in emails:
        if e["attachments"]:
            target = e
            break

    if not target:
        # スプレッドシートURLがあるメールで試す
        for e in emails:
            if e["sheet_urls"]:
                target = e
                break

    if not target:
        logger.info("添付もURLもあるメールなし → スキップ")
        return True

    logger.info(f"テスト対象: UID={target['uid']} 件名={target['subject'][:50]}")

    from ai_extractor import extract_engineers
    from file_parser import parse_file
    from notion_writer import check_duplicate

    # 添付ファイルがあればパース→抽出まで試す（登録はしない）
    if target["attachments"]:
        att = target["attachments"][0]
        logger.info(f"添付ファイル処理: {att['filename']}")
        text = parse_file(att["filename"], att["ext"], att["data"])
        if text:
            logger.info(f"テキスト変換OK ({len(text)}文字)")
            engineers = extract_engineers(text, att["filename"])
            if engineers:
                logger.info(f"抽出OK: {len(engineers)}名")
                for eng in engineers:
                    name = eng.get("name", "不明")
                    dup = check_duplicate(name)
                    logger.info(f"  {name} - 重複:{dup}")
            else:
                logger.warning("抽出結果0名")
        else:
            logger.warning("テキスト変換失敗")

    if target["sheet_urls"]:
        logger.info(f"スプレッドシートURL: {target['sheet_urls'][0][:60]}")
        # Playwright必要なのでここでは接続テストのみ
        try:
            from sheet_fetcher import fetch_sheet_text

            logger.info("sheet_fetcher import OK")
        except ImportError as e:
            logger.warning(f"sheet_fetcher import失敗: {e}")

    return True


def main():
    logger.info("========== 統合テスト開始 ==========")

    # Step 1
    emails = test_imap_connection()
    if emails is None:
        logger.error("IMAP接続失敗 → テスト中断")
        logger.error("※ ses-mailが動いている環境からなら接続できるはず")
        sys.exit(1)

    # Step 2
    test_file_parser()

    # Step 3
    if not test_ai_extractor():
        logger.error("Claude API接続失敗 → テスト中断")
        sys.exit(1)

    # Step 4
    test_notion_writer()

    # Step 5
    test_full_pipeline(emails)

    logger.info("========== 統合テスト完了 ==========")


if __name__ == "__main__":
    main()
