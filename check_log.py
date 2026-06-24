import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log_path = os.path.expandvars(r"%LOCALAPPDATA%\Claude\logs\chrome-native-host.log")
with open(log_path, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# 末尾200行を出力
for line in lines[-200:]:
    print(line, end="")
