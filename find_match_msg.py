# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# line_webhookディレクトリ内の全.pyファイルで検索
webhook_dir = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
targets = ["マッチ案件なし", "有効案件なし", "スキル・粗利", "matsuno", "[matsuno]"]

for py_file in webhook_dir.glob("*.py"):
    try:
        content = py_file.read_text(encoding="utf-8", errors="replace")
        for t in targets:
            if t in content:
                lines = content.splitlines()
                for i, line in enumerate(lines, 1):
                    if t in line:
                        print(f"{py_file.name}:{i}: {line.strip()[:120]}")
    except Exception:
        pass
