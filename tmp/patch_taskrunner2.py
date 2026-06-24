#!/usr/bin/env python3
"""task_runner.py パッチ: save時にゲート自動実行"""

import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = os.path.join(os.path.expanduser("~"), "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
tr_path = os.path.join(base, "local_server", "task_runner.py")

src = open(tr_path, encoding="utf-8").read()
if "gate_on_save" in src:
    print("既にパッチ済みです。スキップ。")
    sys.exit(0)

shutil.copy(tr_path, tr_path + ".bak")
print("backup OK")

# 追加するコードを別ファイルから読み込む方式で埋め込む
addition_path = os.path.join(base, "tmp", "save_gate_addition.py")
addition = open(addition_path, encoding="utf-8").read()

old_save = 'def save_task(title: str, content: str) -> str:\n    """指示書をpending_tasks/に保存"""\n    os.makedirs(PENDING_DIR, exist_ok=True)\n    num = get_next_number()\n    filename = f"{num:03d}_{title}.md"\n    filepath = os.path.join(PENDING_DIR, filename)\n    with open(filepath, "w", encoding="utf-8") as f:\n        f.write(content)\n    print(f"保存完了: {filename}")\n    return filename'

src = src.replace(old_save, addition)
open(tr_path, "w", encoding="utf-8").write(src)
print("task_runner.py パッチ完了")

r = subprocess.run([sys.executable, "-m", "py_compile", tr_path], capture_output=True, encoding="utf-8")
if r.returncode == 0:
    print("構文チェック OK")
else:
    print("構文エラー:", r.stderr)
    shutil.copy(tr_path + ".bak", tr_path)
    print("バックアップから復元しました")
