"""ダイジェスト送信スクリプト。schtasks で 12:00 / 18:00 JST に呼び出す。

登録例（管理者PowerShellで実行）:
  $py = (Get-Command python).Source
  $script = "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\task_auto_runner\digest_sender.py"
  schtasks /create /tn "runner_digest_1200" /tr "$py $script" /sc daily /st 12:00 /f
  schtasks /create /tn "runner_digest_1800" /tr "$py $script" /sc daily /st 18:00 /f
"""

import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

from notifier import flush_notify_queue

if __name__ == "__main__":
    label = datetime.now().strftime("%H:%M")
    sent = flush_notify_queue(label=label)
    print(f"digest_sender: sent={sent} label={label}")
