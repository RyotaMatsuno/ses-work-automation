import json
import shutil

config_path = r"C:\Users\ma_py\AppData\Roaming\Claude\claude_desktop_config.json"
bak_path = config_path + ".bak_before_mcp_add"

shutil.copy2(config_path, bak_path)
print(f"Backup: {bak_path}")

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

NPX = r"C:\Program Files\nodejs\npx.cmd"
DESKTOP = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

print("Existing MCP keys:", list(config["mcpServers"].keys()))

# memory
config["mcpServers"]["memory"] = {
    "command": NPX,
    "args": ["-y", "@modelcontextprotocol/server-memory"],
    "env": {"MEMORY_FILE_PATH": DESKTOP + r"\mcp_data\memory.json"},
}

# sequentialthinking
config["mcpServers"]["sequentialthinking"] = {
    "command": NPX,
    "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
}

# context7
config["mcpServers"]["context7"] = {"command": NPX, "args": ["-y", "@upstash/context7-mcp"]}

# firecrawl (APIキー取得後に要差し替え)
config["mcpServers"]["firecrawl"] = {
    "command": NPX,
    "args": ["-y", "firecrawl-mcp"],
    "env": {"FIRECRAWL_API_KEY": "REPLACE_WITH_API_KEY"},
}

# github (PAT取得後に要差し替え)
config["mcpServers"]["github"] = {
    "command": NPX,
    "args": ["-y", "@github/mcp-server"],
    "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "REPLACE_WITH_PAT"},
}

with open(config_path, "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

# 検証
with open(config_path, "r", encoding="utf-8") as f:
    verify = json.load(f)

print("Updated MCP keys:", list(verify["mcpServers"].keys()))
print("memory path:", verify["mcpServers"]["memory"]["env"]["MEMORY_FILE_PATH"])
print("JSON OK")
