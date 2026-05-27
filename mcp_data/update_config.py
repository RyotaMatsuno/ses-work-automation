
import json
import shutil

config_path = r'C:\Users\ma_py\AppData\Roaming\Claude\claude_desktop_config.json'
bak_path = config_path + '.bak3'

# バックアップ
shutil.copy2(config_path, bak_path)
print(f'Backup: {bak_path}')

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

NPX = r'C:\Program Files\nodejs\npx.cmd'
DESKTOP = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work'

# memory: node.exe直接 → npx経由に変更
config['mcpServers']['memory'] = {
    "command": NPX,
    "args": ["-y", "@modelcontextprotocol/server-memory"],
    "env": {
        "MEMORY_FILE_PATH": DESKTOP + r'\mcp_data\memory.json'
    }
}

# sequentialthinking: node.exe直接 → npx経由
config['mcpServers']['sequentialthinking'] = {
    "command": NPX,
    "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
}

# context7: node.exe直接 → npx経由
config['mcpServers']['context7'] = {
    "command": NPX,
    "args": ["-y", "@upstash/context7-mcp"]
}

# Firecrawl（APIキー取得後に差し替え）
config['mcpServers']['firecrawl'] = {
    "command": NPX,
    "args": ["-y", "firecrawl-mcp"],
    "env": {
        "FIRECRAWL_API_KEY": "REPLACE_WITH_API_KEY"
    }
}

# GitHub（PAT取得後に差し替え）
config['mcpServers']['github'] = {
    "command": NPX,
    "args": ["-y", "@github/mcp-server"],
    "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "REPLACE_WITH_PAT"
    }
}

with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print('Config updated.')
print('MCP keys:', list(config['mcpServers'].keys()))

# 検証
with open(config_path, 'r', encoding='utf-8') as f:
    verify = json.load(f)
print('Verify JSON: OK')
for k, v in verify['mcpServers'].items():
    print(f'  {k}: {v["command"]}')
