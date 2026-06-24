import asyncio

from playwright.async_api import async_playwright


async def get_sheet_text(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=15000)
            await page.wait_for_timeout(3000)

            # ログイン画面チェック
            current_url = page.url
            if "accounts.google.com" in current_url or "login" in current_url.lower():
                await browser.close()
                print(json.dumps({"status": "login_required", "url": url}))
                return

            # ページテキスト取得
            text = await page.inner_text("body")
            await browser.close()
            result = {"status": "ok", "url": url, "text": text[:50000]}
            print(json.dumps(result, ensure_ascii=False))

        except Exception as e:
            await browser.close()
            print(json.dumps({"status": "error", "url": url, "error": str(e)}))


import sys

url = sys.argv[1] if len(sys.argv) > 1 else ""
asyncio.run(get_sheet_text(url))
