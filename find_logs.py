import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# MCPサーバーのデバッグログを探す
base = os.path.expandvars(r"%LOCALAPPDATA%\Claude")
for root, dirs, files in os.walk(base):
    for f in files:
        fp = os.path.join(root, f)
        print(fp)

# Electronのログパスも確認
base2 = os.path.expandvars(r"%LOCALAPPDATA%\AnthropicClaude")
if os.path.exists(base2):
    for root, dirs, files in os.walk(base2):
        for f in files:
            print(os.path.join(root, f))
else:
    print("AnthropicClaude folder not found")
