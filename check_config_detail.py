import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

config_path = os.path.expandvars(r"%APPDATA%\Claude\claude_desktop_config.json")
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# mcpServersの各エントリの詳細確認
for name, entry in config["mcpServers"].items():
    print(f"=== {name} ===")
    print(f"  command: {entry.get('command')}")
    print(f"  args: {entry.get('args')}")
    env = entry.get("env", {})
    if env:
        for k, v in env.items():
            if "token" in k.lower() or "key" in k.lower() or "secret" in k.lower() or "password" in k.lower():
                print(f"  env.{k}: ***MASKED***")
            else:
                print(f"  env.{k}: {v}")

    # commandが存在するか確認
    cmd = entry.get("command", "")
    if cmd and cmd != "python":
        if os.path.exists(cmd):
            print("  [command存在: OK]")
        else:
            print(f"  [⚠️ command存在確認不可: {cmd}]")
    print()
