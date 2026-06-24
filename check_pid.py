import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

# PID 20652が生きているか確認
result = subprocess.run(
    ["tasklist", "/FI", "PID eq 20652"], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print(result.stdout)

# codex関連プロセス一覧
result2 = subprocess.run(
    ["tasklist", "/FI", "IMAGENAME eq node.exe"], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print(result2.stdout)
