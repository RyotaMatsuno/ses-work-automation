# -*- coding: utf-8 -*-
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
WATCHER = os.path.join(SES, "local_server", "pending_watcher.py")

watcher_code = r'''# -*- coding: utf-8 -*-
"""
pending_tasks/ を監視してCursorに自動投入するウォッチャー。
タスクスケジューラ SES_PendingWatcher で5分おきに実行。
"""
import sys, os, json, subprocess
from pathlib import Path
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
PENDING_DIR = BASE_DIR / "pending_tasks"
DONE_DIR = BASE_DIR / "done_tasks"
NOTIFIED_FILE = BASE_DIR / "local_server" / "pending_notified.json"
CURSOR_INJECT = BASE_DIR / "local_server" / "cursor_inject.py"
LOG_FILE = BASE_DIR / "local_server" / "pending_watcher.log"


def log(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_notified() -> set:
    try:
        if NOTIFIED_FILE.exists():
            return set(json.loads(NOTIFIED_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    return set()


def save_notified(notified: set):
    try:
        NOTIFIED_FILE.parent.mkdir(parents=True, exist_ok=True)
        NOTIFIED_FILE.write_text(json.dumps(sorted(notified), ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def get_pending_files() -> list:
    files = [p.name for p in PENDING_DIR.glob("*.md") if p.name != ".gitkeep"]
    return sorted(files)


def inject_to_cursor(text: str) -> bool:
    try:
        r = subprocess.run(
            [sys.executable, str(CURSOR_INJECT), text],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30, cwd=str(BASE_DIR)
        )
        if r.returncode == 0:
            log(f"Cursor投入成功: {text[:40]}")
            return True
        log(f"Cursor投入失敗: {r.stderr[:100]}")
        return False
    except Exception as e:
        log(f"Cursor投入例外: {e}")
        return False


def main():
    pending = get_pending_files()

    # done_tasks内のファイルをnotifiedから除外
    notified = load_notified()
    if DONE_DIR.exists():
        done = {p.name for p in DONE_DIR.glob("*.md")}
        notified -= done

    if not pending:
        save_notified(notified)
        return

    new_files = [f for f in pending if f not in notified]
    if not new_files:
        return

    log(f"新規pending {len(new_files)}件: {new_files}")

    success = inject_to_cursor("pending_tasks/ を確認して順番に実行してください")
    if success:
        notified.update(new_files)
        save_notified(notified)


if __name__ == "__main__":
    main()
'''

with open(WATCHER, "w", encoding="utf-8") as f:
    f.write(watcher_code)
print("pending_watcher.py 作成完了")

# タスクスケジューラ登録
python_exe = sys.executable.replace("python.exe", "pythonw.exe")
r = subprocess.run(
    [
        "schtasks",
        "/create",
        "/tn",
        "SES_PendingWatcher",
        "/tr",
        f'"{python_exe}" "{WATCHER}"',
        "/sc",
        "MINUTE",
        "/mo",
        "5",
        "/ru",
        "ma_py",
        "/f",
    ],
    capture_output=True,
    timeout=15,
)
out = r.stdout.decode("cp932", errors="replace")
print("スケジューラ登録:", out.strip() or r.stderr.decode("cp932", errors="replace")[:100])

# 動作テスト（ドライラン）
r2 = subprocess.run(
    [sys.executable, WATCHER], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=SES, timeout=20
)
print("動作テスト:", r2.stdout.strip() or "(出力なし)")

# スケジューラ確認
r3 = subprocess.run(["schtasks", "/query", "/tn", "SES_PendingWatcher", "/fo", "LIST"], capture_output=True, timeout=10)
out3 = r3.stdout.decode("cp932", errors="replace")
status = "登録済み" if "準備完了" in out3 or "実行中" in out3 else "未登録"
print(f"スケジューラ状態: {status}")
