import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

config_path = os.path.expandvars(r"%APPDATA%\Claude\claude_desktop_config.json")

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

node_exe = r"C:\Program Files\nodejs\node.exe"
npm_modules = r"C:\Users\ma_py\AppData\Roaming\npm\node_modules"

# memory
config["mcpServers"]["memory"] = {
    "command": node_exe,
    "args": [os.path.join(npm_modules, r"@modelcontextprotocol\server-memory\dist\index.js")],
    "env": {"MEMORY_FILE_PATH": r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mcp_data\memory.json"},
}

# sequentialthinking
config["mcpServers"]["sequentialthinking"] = {
    "command": node_exe,
    "args": [os.path.join(npm_modules, r"@modelcontextprotocol\server-sequential-thinking\dist\index.js")],
}

# context7
config["mcpServers"]["context7"] = {
    "command": node_exe,
    "args": [os.path.join(npm_modules, r"@upstash\context7-mcp\dist\index.js")],
}

with open(config_path, "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

# 検証
with open(config_path, "r", encoding="utf-8") as f:
    check = json.load(f)

print("✅ 書き込み完了")
print(f"mcpServers登録数: {len(check['mcpServers'])}本")
print()
for name in ["memory", "sequentialthinking", "context7"]:
    entry = check["mcpServers"][name]
    cmd = entry["command"]
    arg0 = entry["args"][0]
    exists_cmd = os.path.exists(cmd)
    exists_arg = os.path.exists(arg0)
    print(f"{name}:")
    print(f"  command: {cmd} [{'✅' if exists_cmd else '❌'}]")
    print(f"  args[0]: {arg0} [{'✅' if exists_arg else '❌'}]")
