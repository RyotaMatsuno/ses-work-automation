"""Shared Google Spreadsheet text fetcher (OAuth API + Playwright fallback)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

SPREADSHEET_ID_RE = re.compile(r"https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)")
TOKEN_URI = "https://oauth2.googleapis.com/token"


def extract_spreadsheet_id(url: str) -> str | None:
    match = SPREADSHEET_ID_RE.search(url or "")
    return match.group(1) if match else None


def _load_oauth_credentials(token_path: Path):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token_data = json.loads(token_path.read_text(encoding="utf-8"))
    access_token = token_data.get("access_token") or token_data.get("token")
    creds = Credentials(
        token=access_token,
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri") or TOKEN_URI,
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes")
        or [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
    if not creds.valid:
        creds.refresh(Request())
        token_data["access_token"] = creds.token
        token_data["token"] = creds.token
        token_path.write_text(json.dumps(token_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return creds


def fetch_sheet_text_via_oauth(url: str, token_path: str | Path) -> dict:
    sheet_id = extract_spreadsheet_id(url)
    if not sheet_id:
        return {"status": "error", "error": "invalid_spreadsheet_url", "url": url}

    path = Path(token_path)
    if not path.exists():
        return {"status": "error", "error": f"token_not_found: {path}", "url": url}

    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        creds = _load_oauth_credentials(path)
        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range="A1:ZZ1000")
            .execute()
        )
        rows = result.get("values", [])
        lines = ["\t".join(str(cell) for cell in row) for row in rows if row]
        text = "\n".join(lines)
        if not text.strip():
            return {"status": "error", "error": "empty_sheet", "url": url}
        logger.info("OAuth sheet fetch ok: %s (%d chars)", url, len(text))
        return {"status": "ok", "url": url, "text": text[:50000]}
    except Exception as exc:
        status_code = getattr(getattr(exc, "resp", None), "status", None)
        if status_code in (403, 404):
            logger.info("OAuth sheet permission error: %s (%s)", url, exc)
            return {"status": "login_required", "url": url, "error": str(exc)}
        if exc.__class__.__name__ == "HttpError":
            return {"status": "login_required", "url": url, "error": str(exc)}
        logger.warning("OAuth sheet fetch failed: %s (%s)", url, exc)
        return {"status": "error", "url": url, "error": str(exc)}


def fetch_sheet_text_playwright(url: str) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "status": "error",
            "error": "playwright未インストール: pip install playwright && python -m playwright install chromium",
            "url": url,
        }

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, timeout=15000)
                page.wait_for_timeout(3000)
                current_url = page.url
                if "accounts.google.com" in current_url or "ServiceLogin" in current_url:
                    logger.info("Playwright login required: %s", url)
                    return {"status": "login_required", "url": url}
                text = page.inner_text("body")
                logger.info("Playwright sheet fetch ok: %s (%d chars)", url, len(text))
                return {"status": "ok", "url": url, "text": text[:50000]}
            finally:
                browser.close()
    except Exception as exc:
        logger.error("Playwright sheet fetch failed: %s (%s)", url, exc)
        return {"status": "error", "url": url, "error": str(exc)}


def fetch_sheet_text(url: str, oauth_token_path: str | Path | None = None) -> dict:
    if oauth_token_path:
        oauth_result = fetch_sheet_text_via_oauth(url, oauth_token_path)
        if oauth_result.get("status") == "ok":
            return oauth_result
        logger.info(
            "OAuth fetch status=%s, fallback to playwright: %s",
            oauth_result.get("status"),
            url,
        )
    return fetch_sheet_text_playwright(url)
