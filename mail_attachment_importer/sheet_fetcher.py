"""
sheet_fetcher.py - Google Spreadsheetのテキスト取得モジュール
Playwright sync_apiでブラウザ経由取得
"""

import logging
import sys

logger = logging.getLogger(__name__)


def fetch_sheet_text(url: str) -> dict:
    """
    Google SpreadsheetのURLからテキストを取得する。

    Returns:
        dict:
            status: "ok" | "login_required" | "error"
            text: str (status=="ok"のとき)
            error: str (status=="error"のとき)
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "status": "error",
            "error": "playwright未インストール: pip install playwright && python -m playwright install chromium",
        }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                page.goto(url, timeout=15000)
                page.wait_for_timeout(3000)

                current_url = page.url
                if "accounts.google.com" in current_url or "ServiceLogin" in current_url:
                    browser.close()
                    logger.info(f"ログイン必要のためスキップ: {url}")
                    return {"status": "login_required", "url": url}

                text = page.inner_text("body")
                browser.close()

                logger.info(f"スプレッドシート取得成功: {url} ({len(text)}文字)")
                return {"status": "ok", "url": url, "text": text[:50000]}

            except Exception as e:
                browser.close()
                return {"status": "error", "error": str(e)}

    except Exception as e:
        logger.error(f"sheet_fetcher exception: {e}")
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://docs.google.com/spreadsheets/d/1F1vHkcta_oUpEu-BxLIO1c0FBp4TfRJ0/edit"
    )
    result = fetch_sheet_text(test_url)
    print(f"status: {result['status']}")
    if result.get("text"):
        print(f"text ({len(result['text'])}文字):\n{result['text'][:500]}")
    if result.get("error"):
        print(f"error: {result['error']}")
