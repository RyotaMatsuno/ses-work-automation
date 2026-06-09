"""Collect active window + screenshot every scheduler run."""
from __future__ import annotations

import logging
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
SES_WORK = BASE_DIR.parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
LOG_DIR = BASE_DIR / "logs"
JST = timezone(timedelta(hours=9))

COLLECTION_START_HOUR = 8
COLLECTION_END_HOUR = 20
SCREENSHOT_RETENTION_DAYS = 7
DB_RETENTION_DAYS = 30

from db import cleanup_old_records, insert_activity  # noqa: E402
from ocr import extract_text  # noqa: E402


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"collector_{datetime.now(JST).strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def is_collection_window(now: datetime | None = None) -> bool:
    current = now or datetime.now(JST)
    return COLLECTION_START_HOUR <= current.hour < COLLECTION_END_HOUR


def get_active_window() -> tuple[str, str]:
    title = ""
    app_name = ""

    try:
        import win32gui
        import win32process

        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            title = win32gui.GetWindowText(hwnd) or ""
            import os
            import win32api

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                handle = win32api.OpenProcess(0x1000, False, pid)
                exe_path = win32process.GetModuleFileNameEx(handle, 0)
                win32api.CloseHandle(handle)
                app_name = os.path.basename(exe_path)
            except Exception:
                app_name = ""
    except Exception as exc:
        logging.warning("win32gui failed: %s", exc)

    if not title:
        try:
            import pygetwindow as gw

            window = gw.getActiveWindow()
            if window:
                title = window.title or ""
                app_name = app_name or (Path(window.title).stem if window.title else "")
        except Exception as exc:
            logging.warning("pygetwindow failed: %s", exc)

    if not app_name and title:
        app_name = title.split(" - ")[-1].strip() if " - " in title else title[:64]

    return app_name or "不明", title


def capture_screenshot(dest: Path) -> Path | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import ImageGrab

        image = ImageGrab.grab()
        image.save(dest, format="JPEG", quality=50, optimize=True)
        return dest
    except Exception as exc:
        logging.error("screenshot failed: %s", exc)
        return None


def cleanup_old_screenshots(days: int = SCREENSHOT_RETENTION_DAYS) -> int:
    if not SCREENSHOTS_DIR.exists():
        return 0
    cutoff = (datetime.now(JST) - timedelta(days=days)).date()
    removed = 0
    for child in SCREENSHOTS_DIR.iterdir():
        if not child.is_dir():
            continue
        try:
            folder_date = datetime.strptime(child.name, "%Y-%m-%d").date()
        except ValueError:
            continue
        if folder_date < cutoff:
            shutil.rmtree(child, ignore_errors=True)
            removed += 1
            logging.info("removed old screenshot dir: %s", child.name)
    return removed


def collect_once() -> None:
    now = datetime.now(JST)
    if not is_collection_window(now):
        logging.info("outside collection window (%s:00-%s:00), skip", COLLECTION_START_HOUR, COLLECTION_END_HOUR)
        return

    app_name, window_title = get_active_window()
    day_dir = SCREENSHOTS_DIR / now.strftime("%Y-%m-%d")
    shot_name = now.strftime("%H%M%S") + ".jpg"
    shot_path = day_dir / shot_name

    saved = capture_screenshot(shot_path)
    screenshot_path = str(saved) if saved else None

    ocr_text: str | None = None
    if saved:
        text = extract_text(saved)
        if text:
            ocr_text = text

    insert_activity(
        timestamp=now.isoformat(),
        app_name=app_name,
        window_title=window_title,
        ocr_text=ocr_text,
        screenshot_path=screenshot_path,
    )
    logging.info(
        "saved activity app=%s title=%s ocr=%s",
        app_name,
        (window_title or "")[:80],
        "yes" if ocr_text else "no",
    )


def main() -> int:
    setup_logging()
    try:
        collect_once()
        cleanup_old_screenshots()
        deleted = cleanup_old_records(DB_RETENTION_DAYS)
        if deleted:
            logging.info("deleted old db records: %s", deleted)
    except Exception as exc:
        logging.exception("collector error: %s", exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
