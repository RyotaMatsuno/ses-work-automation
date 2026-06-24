import json
import re
from pathlib import Path

from playwright.sync_api import Page, TimeoutError, sync_playwright

BASE_DIR = Path(__file__).resolve().parent
SESSION_FILE = BASE_DIR / "okamoto_session.json"
CHANNELS_FILE = BASE_DIR / "okamoto_channels.json"
LOGIN_URL = "https://developers.line.biz/console/"
CHANNEL_LINK_RE = re.compile(r"/console/channel/(\d+)/")


def save_channels(page: Page) -> None:
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except TimeoutError:
        pass

    links = page.eval_on_selector_all(
        "a[href*='/console/channel/']",
        """elements => elements.map((element) => ({
            href: element.href || element.getAttribute('href') || '',
            text: (element.innerText || element.textContent || '').trim(),
            title: element.getAttribute('title') || '',
            ariaLabel: element.getAttribute('aria-label') || ''
        }))""",
    )

    channels = []
    seen_ids = set()
    for link in links:
        match = CHANNEL_LINK_RE.search(link.get("href", ""))
        if not match:
            continue

        channel_id = match.group(1)
        if channel_id in seen_ids:
            continue

        name = link.get("text") or link.get("title") or link.get("ariaLabel") or f"channel_{channel_id}"
        channels.append({"name": name, "id": channel_id})
        seen_ids.add(channel_id)

    if not channels:
        print("CHANNELS_NOT_FOUND")
        return

    CHANNELS_FILE.write_text(
        json.dumps(channels, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"CHANNELS_SAVED: {len(channels)}件")
    for channel in channels:
        print(f"- {channel['name']}: {channel['id']}")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(LOGIN_URL, wait_until="domcontentloaded")

            input("LINE Developers Consoleへのログイン完了後、Enterを押してください: ")

            page.goto(LOGIN_URL, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except TimeoutError:
                pass

            cookies = context.cookies()
            if not cookies:
                print("SESSION_SAVE_FAILED no_cookies")
                raise SystemExit(1)

            SESSION_FILE.write_text(
                json.dumps(cookies, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"SESSION_SAVED {SESSION_FILE} cookies={len(cookies)}")
            save_channels(page)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
