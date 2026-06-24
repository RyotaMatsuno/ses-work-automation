# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"

# 008の中身を正しい設計に差し替え
task = """# 【Cursor作業指示】pending_watcher - Composerへの自動通知

対象: ses_work/local_server/pending_watcher.py（新規作成）
優先度: P1

## 設計方針（ジョブズ確定）

pending_tasksにファイルが追加されたら、
jobz-command経由で松野LINEに「Cursorでpending_tasksを実行してください」と通知する。
CursorのUI自動操作（pyautogui）は使わない（環境依存リスクが高い）。
コードの自動生成・自動実行もしない（ゲート②スキップになるため）。

「Cursorを開くだけ」ではなく「LINEに通知が来たらComposerで実行する」運用に変更。
（これが現実的な自動化の限界。コード自動実行はリスクが高すぎる）

ただし通知はpush_or_log()経由（月200通上限対応済み）。

---

## 実装: ses_work/local_server/pending_watcher.py

```python
# -*- coding: utf-8 -*-
\"\"\"
pending_tasks/ を監視して松野LINEに通知するウォッチャー。
Windowsタスクスケジューラ「SES_PendingWatcher」で5分おきに実行。
\"\"\"
import sys, os, json, glob
from pathlib import Path
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(r"C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work")
PENDING_DIR = BASE_DIR / "pending_tasks"
NOTIFIED_FILE = BASE_DIR / "local_server" / "pending_notified.json"


def load_notified() -> set:
    try:
        if NOTIFIED_FILE.exists():
            return set(json.loads(NOTIFIED_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    return set()


def save_notified(notified: set):
    NOTIFIED_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTIFIED_FILE.write_text(json.dumps(list(notified), ensure_ascii=False), encoding="utf-8")


def get_pending_files() -> list[str]:
    files = [p.name for p in PENDING_DIR.glob("*.md") if p.name != ".gitkeep"]
    return sorted(files)


def push_line(message: str) -> bool:
    try:
        from dotenv import dotenv_values
        import urllib.request
        env = dotenv_values(BASE_DIR / "config" / ".env")
        token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
        user_id = env.get("MATSUNO_LINE_USER_ID", "") or env.get("MATSUNO_USER_ID", "")
        if not token or not user_id:
            return False

        # 残通数確認
        import requests
        r_quota = requests.get("https://api.line.me/v2/bot/message/quota",
                               headers={"Authorization": f"Bearer {token}"}, timeout=5)
        r_used = requests.get("https://api.line.me/v2/bot/message/quota/consumption",
                              headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if r_quota.status_code == 200 and r_used.status_code == 200:
            remaining = r_quota.json().get("value", 200) - r_used.json().get("totalUsage", 0)
            if remaining <= 0:
                print(f"LINE残0通のためスキップ: {message[:30]}")
                return False

        payload = json.dumps({"to": user_id, "messages": [{"type": "text", "text": message}]},
                             ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push", data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception as e:
        print(f"push失敗: {e}")
        return False


def main():
    pending = get_pending_files()
    if not pending:
        print("pending_tasks: 空")
        return

    notified = load_notified()
    new_files = [f for f in pending if f not in notified]

    if not new_files:
        print(f"通知済みのファイルのみ: {pending}")
        return

    # 新規ファイルを通知
    file_list = "\\n".join(f"・{f}" for f in new_files[:5])
    message = (
        f"📋 Cursorタスクが{len(new_files)}件あります\\n"
        f"{file_list}\\n\\n"
        "Cursorのcomposerに↓を貼ってください:\\n"
        "pending_tasks/ を確認して順番に実行してください"
    )
    success = push_line(message)
    if success:
        notified.update(new_files)
        save_notified(notified)
        print(f"通知送信: {new_files}")
    else:
        print(f"通知失敗（LINE上限等）: {new_files}")

    # done_tasks/に移動したファイルをnotifiedから削除（クリーンアップ）
    done_dir = BASE_DIR / "done_tasks"
    if done_dir.exists():
        done_files = {p.name for p in done_dir.glob("*.md")}
        notified -= done_files
        save_notified(notified)


if __name__ == "__main__":
    main()
```

## タスクスケジューラ登録

```python
import subprocess
subprocess.run([
    "schtasks", "/create", "/tn", "SES_PendingWatcher",
    "/tr", r'pythonw "C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work\\local_server\\pending_watcher.py"',
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
「Cursorタスクが〇件あります」のLINE通知が来ればOK。
（LINE残0通の場合は「スキップ」と出るが正常動作）

```
schtasks /query /tn SES_PendingWatcher /fo LIST
```
「準備完了」が出ればOK。

完了後に「pending_watcher完了」とClaude.aiに報告すること。
"""

# 既存008を差し替え
for f in os.listdir(PENDING):
    if f.startswith("008"):
        os.remove(os.path.join(PENDING, f))
        print(f"削除: {f}")

path = os.path.join(PENDING, "008_pending_watcher.md")
with open(path, "w", encoding="utf-8") as f:
    f.write(task)
print("保存: 008_pending_watcher.md")
print(f"\npending_tasks: {sorted(os.listdir(PENDING))}")
