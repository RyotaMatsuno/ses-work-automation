import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import Error, Locator, Page, TimeoutError, sync_playwright

BASE_DIR = Path(__file__).resolve().parent
SESSION_FILE = BASE_DIR / "okamoto_session.json"
CONSOLE_URL = "https://developers.line.biz/console/"
CHANNEL_URL = "https://developers.line.biz/console/channel/{channel_id}/messaging-api"


def load_cookies() -> list[dict]:
    if not SESSION_FILE.exists():
        print("SESSION_EXPIRED")
        raise SystemExit(1)

    try:
        cookies = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("SESSION_EXPIRED")
        raise SystemExit(1)

    if not isinstance(cookies, list) or not cookies:
        print("SESSION_EXPIRED")
        raise SystemExit(1)

    return cookies


def is_logged_in(page: Page) -> bool:
    page.goto(CONSOLE_URL, wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except TimeoutError:
        pass

    title = page.title()
    current_url = page.url.lower()
    if "login" in current_url or "account.line.biz" in current_url:
        return False
    return "console" in title.lower()


def click_first_visible(locator: Locator, timeout: int = 3000) -> bool:
    try:
        locator.first.wait_for(state="visible", timeout=timeout)
    except TimeoutError:
        return False

    for index in range(locator.count()):
        item = locator.nth(index)
        if item.is_visible() and item.is_enabled():
            item.click()
            return True
    return False


def fill_first_visible(locator: Locator, value: str, timeout: int = 3000) -> bool:
    try:
        locator.first.wait_for(state="visible", timeout=timeout)
    except TimeoutError:
        return False

    for index in range(locator.count()):
        item = locator.nth(index)
        if item.is_visible() and item.is_enabled():
            item.fill(value)
            return True
    return False


def open_webhook_editor(page: Page) -> None:
    settings = page.locator(
        "section:has-text('Webhook settings'), div:has-text('Webhook settings'), "
        "section:has-text('Webhook設定'), div:has-text('Webhook設定')"
    ).first

    edit_button = settings.get_by_role("button", name=re.compile(r"Edit|編集|変更", re.IGNORECASE))
    if click_first_visible(edit_button):
        return

    global_edit_button = page.get_by_role("button", name=re.compile(r"Edit|編集|変更", re.IGNORECASE))
    click_first_visible(global_edit_button, timeout=1000)


def fill_webhook_url(page: Page, webhook_url: str) -> None:
    label_pattern = re.compile(r"Webhook URL|Webhook URL設定|ウェブフックURL", re.IGNORECASE)
    if fill_first_visible(page.get_by_label(label_pattern), webhook_url):
        return

    selector = (
        "input[type='url'], input[name*='webhook' i], "
        "input[placeholder*='webhook' i], textarea[name*='webhook' i], "
        "input[type='text'], textarea"
    )
    settings = page.locator(
        "section:has-text('Webhook settings'), div:has-text('Webhook settings'), "
        "section:has-text('Webhook設定'), div:has-text('Webhook設定')"
    ).first
    if fill_first_visible(settings.locator(selector), webhook_url, timeout=1000):
        return
    if fill_first_visible(page.locator(selector), webhook_url, timeout=1000):
        return

    print("WEBHOOK_INPUT_NOT_FOUND")
    raise SystemExit(1)


def save_webhook_url(page: Page) -> None:
    save_button = page.get_by_role("button", name=re.compile(r"Save|Update|保存|更新|変更", re.IGNORECASE))
    if not click_first_visible(save_button):
        print("SAVE_BUTTON_NOT_FOUND")
        raise SystemExit(1)

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except TimeoutError:
        pass


def set_webhook(channel_id: str, webhook_url: str, headless: bool = True) -> None:
    cookies = load_cookies()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()

        try:
            if not is_logged_in(page):
                print("SESSION_EXPIRED")
                raise SystemExit(1)

            page.goto(
                CHANNEL_URL.format(channel_id=channel_id),
                wait_until="domcontentloaded",
            )
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except TimeoutError:
                pass

            if "login" in page.url.lower():
                print("SESSION_EXPIRED")
                raise SystemExit(1)

            open_webhook_editor(page)
            fill_webhook_url(page, webhook_url)
            save_webhook_url(page)
            print(f"WEBHOOK_UPDATED channel_id={channel_id}")
        except Error as exc:
            print(f"PLAYWRIGHT_ERROR {exc.__class__.__name__}: {exc}")
            raise SystemExit(1)
        finally:
            browser.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel-id", required=True)
    parser.add_argument("--webhook-url", required=True)
    parser.add_argument("--headed", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_webhook(args.channel_id, args.webhook_url, headless=not args.headed)


if __name__ == "__main__":
    main()
