# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"

# 008を完全に差し替え
for f in os.listdir(PENDING):
    if f.startswith("008"):
        os.remove(os.path.join(PENDING, f))

task = """# 【Cursor作業指示】pending_watcher v2 - Cursor自動投入版

対象: ses_work/local_server/pending_watcher.py（更新）
優先度: P1

## 設計（確定）

pyautoguiとcursor_inject.pyを使い、pending_tasksに新ファイルが追加されたら
Cursorのエージェント/ComposerにLINE送信のかわりに直接テキストを投入する。
タスクスケジューラで5分おきに実行。

cursor_inject.pyは local_server/cursor_inject.py に既に存在・動作確認済み。

---

## pending_watcher.py を以下に全文差し替え

```python
# -*- coding: utf-8 -*-
\"\"\"
pending_tasks/ を監視してCursorに自動投入するウォッチャー。
タスクスケジューラ SES_PendingWatcher で5分おきに実行。
\"\"\"
import sys, os, json, subprocess, time
from pathlib import Path
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(r"C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work")
PENDING_DIR = BASE_DIR / "pending_tasks"
DONE_DIR = BASE_DIR / "done_tasks"
NOTIFIED_FILE = BASE_DIR / "local_server" / "pending_notified.json"
CURSOR_INJECT = BASE_DIR / "local_server" / "cursor_inject.py"
LOG_FILE = BASE_DIR / "local_server" / "pending_watcher.log"


def log(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\\n")


def load_notified() -> set:
    try:
        if NOTIFIED_FILE.exists():
            return set(json.loads(NOTIFIED_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    return set()


def save_notified(notified: set):
    NOTIFIED_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTIFIED_FILE.write_text(json.dumps(sorted(notified), ensure_ascii=False), encoding="utf-8")


def get_pending_files() -> list[str]:
    files = [p.name for p in PENDING_DIR.glob("*.md") if p.name != ".gitkeep"]
    return sorted(files)


def inject_to_cursor(text: str) -> bool:
    \"\"\"cursor_inject.py経由でCursorのComposerにテキストを投入\"\"\"
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

    # done_tasks内のファイルをnotifiedから除外（クリーンアップ）
    notified = load_notified()
    if DONE_DIR.exists():
        done = {p.name for p in DONE_DIR.glob("*.md")}
        notified -= done

    if not pending:
        log("pending_tasks: 空")
        save_notified(notified)
        return

    new_files = [f for f in pending if f not in notified]
    if not new_files:
        log(f"通知済みのみ: {pending}")
        return

    log(f"新規pending {len(new_files)}件: {new_files}")

    # Cursorに投入するテキスト
    inject_text = "pending_tasks/ を確認して順番に実行してください"
    success = inject_to_cursor(inject_text)

    if success:
        notified.update(new_files)
        save_notified(notified)


if __name__ == "__main__":
    main()
```

## タスクスケジューラ登録

```python
import subprocess
subprocess.run([
    "schtasks", "/create", "/tn", "SES_PendingWatcher",
    "/tr", r'python "C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work\\local_server\\pending_watcher.py"',
    "/sc", "MINUTE", "/mo", "5",
    "/ru", "ma_py",
    "/f"
], check=True)
print("SES_PendingWatcher 登録完了（5分おき）")
```

## 完了確認

```
python local_server/pending_watcher.py
```
Cursorのエージェント/Composerに「pending_tasks/ を確認して順番に実行してください」
が自動投入されることを確認。

```
schtasks /query /tn SES_PendingWatcher /fo LIST
```
「準備完了」が出ればOK。

完了後に「pending_watcher完了」とClaude.aiに報告すること。
"""

path = os.path.join(PENDING, "008_pending_watcher.md")
with open(path, "w", encoding="utf-8") as f:
    f.write(task)
print("保存: 008_pending_watcher.md")
print(f"pending_tasks: {sorted(os.listdir(PENDING))}")
