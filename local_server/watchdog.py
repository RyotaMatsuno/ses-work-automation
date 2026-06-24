"""
jobz-command watchdog
command_server.pyが落ちていたら自動再起動するスクリプト
タスクスケジューラで5分おきに実行する
"""

import logging
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\local_server")
LOG_FILE = BASE_DIR / "watchdog.log"
SERVER_URL = "http://127.0.0.1:8765/health"
AUTH_TOKEN = "jobz-terra-2026"
PYTHON_EXE = sys.executable.replace("python.exe", "pythonw.exe")
SERVER_SCRIPT = str(BASE_DIR / "command_server.py")

logging.basicConfig(filename=str(LOG_FILE), level=logging.INFO, format="%(asctime)s %(message)s", encoding="utf-8")


def check_server():
    req = urllib.request.Request(SERVER_URL, headers={"X-Auth-Token": AUTH_TOKEN})
    try:
        urllib.request.urlopen(req, timeout=3)
        return True
    except:
        return False


def start_server():
    subprocess.Popen([PYTHON_EXE, SERVER_SCRIPT], cwd=str(BASE_DIR), creationflags=subprocess.CREATE_NO_WINDOW)
    logging.info("サーバー再起動しました")


if __name__ == "__main__":
    if check_server():
        logging.info("サーバー正常稼働中")
    else:
        logging.info("サーバーダウン検知 → 再起動")
        start_server()
