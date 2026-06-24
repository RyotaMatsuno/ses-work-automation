# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"

task = """# 【Cursor作業指示】pending_tasks 自動実行ウォッチャー

対象: ses_work/local_server/pending_watcher.py（新規作成）
優先度: P1
根拠: 松野がCursorを開くだけでpending_tasksが自動実行される仕組みを作る。

## 背景と設計方針

現状の問題: Cursorを開いただけでは pending_tasks/ は実行されない。
Composerに「pending_tasks実行して」と毎回打つ必要がある。

解決策: Cursorが開いている間、バックグラウンドで
pending_tasks/ を5分おきに監視するPythonスクリプトを作る。
新しいファイルを検知したら jobz-command の /run_bg で
Cursorのエージェントモード（claude --print）を起動して自動実行させる。

ただしCursorのComposerはCLI経由で起動できないため、
**現実的な実装**として以下を採用する:

pending_tasks/ にファイルが追加されたら:
1. そのファイルの内容を読む
2. Claude APIを直接叩いて実装コードを生成させる（Cursor相当）
3. 生成されたコードをそのまま実行する（Pythonファイルのみ）
4. 完了したらdone_tasks/へ移動
5. 結果をジョブズのClaude.aiチャットに報告（Notion経由）

これが「Cursorを開くだけ」の本当の自動化。

---

## 実装

### ファイル: ses_work/local_server/pending_watcher.py

```python
# -*- coding: utf-8 -*-
\"\"\"
pending_tasks/ を監視して自動実行するウォッチャー。
Windowsタスクスケジューラで常駐起動する。
\"\"\"
import sys, os, time, shutil, glob, json, re, subprocess
from pathlib import Path
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(r"C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work")
PENDING_DIR = BASE_DIR / "pending_tasks"
DONE_DIR = BASE_DIR / "done_tasks"
LOG_FILE = BASE_DIR / "local_server" / "pending_watcher.log"
POLL_INTERVAL = 60  # 60秒ごとにチェック
LOCK_FILE = BASE_DIR / "local_server" / "pending_watcher.lock"


def log(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\\n")


def get_pending_files() -> list[Path]:
    \"\"\"番号順にソートされたpending_tasksのmdファイルを返す\"\"\"
    files = [p for p in PENDING_DIR.glob("*.md") if p.name != ".gitkeep"]
    return sorted(files, key=lambda p: p.name)


def is_cursor_instruction(content: str) -> bool:
    \"\"\"Cursor作業指示かどうか判定\"\"\"
    return "【Cursor作業指示】" in content or "Cursor作業指示" in content


def run_via_claude_api(task_file: Path) -> tuple[bool, str]:
    \"\"\"Claude APIを使って指示書を実行する\"\"\"
    try:
        from dotenv import dotenv_values
        env = dotenv_values(BASE_DIR / "config" / ".env")
        api_key = env.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return False, "ANTHROPIC_API_KEY未設定"

        content = task_file.read_text(encoding="utf-8")

        import urllib.request
        payload = json.dumps({
            "model": "claude-sonnet-4-6",
            "max_tokens": 8000,
            "system": (
                "あなたはSES業務自動化システムのコード実装専任AIです。"
                "以下のCursor作業指示書を読み、Pythonコードを実装してください。"
                f"作業ディレクトリ: {BASE_DIR}\\n"
                "実装完了後、実装内容のサマリーを出力してください。"
                "コードブロックは ```python ``` で囲んでください。"
            ),
            "messages": [{"role": "user", "content": content}]
        }, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))
        response_text = data["content"][0]["text"]

        # Pythonコードブロックを抽出して実行
        code_blocks = re.findall(r"```python\\n(.*?)```", response_text, re.DOTALL)
        executed = []
        for i, code in enumerate(code_blocks):
            tmp = BASE_DIR / f"_auto_exec_{task_file.stem}_{i}.py"
            tmp.write_text(code, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(tmp)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=str(BASE_DIR), timeout=120
            )
            executed.append(f"block{i}: exit={result.returncode}\\n{result.stdout[:300]}")
            tmp.unlink(missing_ok=True)

        summary = response_text[:500] + ("\\n\\n実行結果:\\n" + "\\n".join(executed) if executed else "")
        return True, summary

    except Exception as e:
        return False, str(e)


def notify_notion(task_name: str, success: bool, summary: str):
    \"\"\"Notion AI作業キューに完了記録を積む\"\"\"
    try:
        from dotenv import dotenv_values
        import urllib.request
        env = dotenv_values(BASE_DIR / "config" / ".env")
        token = env.get("NOTION_API_KEY", "")
        db_id = env.get("NOTION_AI_QUEUE_DB_ID", "37a450ff-37c0-819a-981b-c2e06ed282bb")
        if not token:
            return
        now = datetime.now().isoformat()
        payload = json.dumps({
            "parent": {"database_id": db_id},
            "properties": {
                "task_id": {"title": [{"text": {"content": f"auto_{task_name[:20]}"}}]},
                "受付元": {"select": {"name": "LINE"}},
                "種別": {"select": {"name": "dev"}},
                "優先度": {"select": {"name": "低"}},
                "締切": {"select": {"name": "今日中"}},
                "入力データ": {"rich_text": [{"text": {"content": summary[:1000]}}]},
                "使用許可": {"select": {"name": "draft-only"}},
                "担当": {"select": {"name": "cursor"}},
                "状態": {"select": {"name": "done" if success else "blocked"}},
                "結果リンク": {"rich_text": [{"text": {"content": f"pending_watcher: {'成功' if success else '失敗'}\\n{summary[:500]}"}}]},
                "人間確認": {"select": {"name": "不要"}},
                "作成日時": {"date": {"start": now}},
                "完了日時": {"date": {"start": now}},
            }
        }, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            "https://api.notion.com/v1/pages",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            },
            method="POST"
        )
        urllib.request.urlopen(req, timeout=15)
        log(f"Notion通知完了: {task_name}")
    except Exception as e:
        log(f"Notion通知失敗: {e}")


def process_one(task_file: Path) -> bool:
    \"\"\"1件のpendingタスクを処理する\"\"\"
    log(f"処理開始: {task_file.name}")
    content = task_file.read_text(encoding="utf-8")

    if not is_cursor_instruction(content):
        log(f"Cursor作業指示ではないためスキップ: {task_file.name}")
        return False

    success, summary = run_via_claude_api(task_file)
    log(f"実行結果: success={success} summary={summary[:100]}")

    # done_tasksに移動
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.move(str(task_file), str(DONE_DIR / task_file.name))
    log(f"完了: {task_file.name} → done_tasks/")

    # Notionに記録
    notify_notion(task_file.stem, success, summary)
    return success


def run_watcher():
    \"\"\"メインループ\"\"\"
    log("pending_watcher 起動")
    while True:
        try:
            files = get_pending_files()
            if files:
                log(f"pending {len(files)}件を検出")
                for f in files:
                    process_one(f)
                    time.sleep(5)  # タスク間に少し待機
            else:
                pass  # 空のときはログ出力しない
        except Exception as e:
            log(f"ウォッチャーエラー: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    # 多重起動防止
    if LOCK_FILE.exists():
        log("すでに起動中のためスキップ")
        sys.exit(0)
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    try:
        run_watcher()
    finally:
        LOCK_FILE.unlink(missing_ok=True)
```

### Windowsタスクスケジューラ登録（Cursorから実行）

```python
import subprocess, sys
subprocess.run([
    "schtasks", "/create", "/tn", "SES_PendingWatcher",
    "/tr", f'pythonw "C:\\\\Users\\\\ma_py\\\\OneDrive\\\\デスクトップ\\\\ses_work\\\\local_server\\\\pending_watcher.py"',
    "/sc", "ONLOGON",
    "/ru", "ma_py",
    "/f"  # 上書き
], check=True)
print("タスクスケジューラ登録完了")
```

## 完了確認

```python
import subprocess, sys
r = subprocess.run(
    ["schtasks", "/query", "/tn", "SES_PendingWatcher", "/fo", "LIST"],
    capture_output=True, timeout=10
)
print(r.stdout.decode("cp932", errors="replace"))
```

「準備完了」または「実行中」が表示されればOK。

完了後に「pending_watcher完了」とClaude.aiに報告すること。
"""

path = os.path.join(PENDING, "008_pending_watcher.md")
with open(path, "w", encoding="utf-8") as f:
    f.write(task)
print("保存: 008_pending_watcher.md")
print(f"pending_tasks: {sorted(os.listdir(PENDING))}")
