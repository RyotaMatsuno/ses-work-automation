import json

path = r"C:\Users\ma_py\AppData\Roaming\Claude\claude_desktop_config.json"
with open(path, "r", encoding="utf-8") as f:
    d = json.load(f)
print("memory path:", d["mcpServers"]["memory"]["env"]["MEMORY_FILE_PATH"])
print("firecrawl placeholder:", d["mcpServers"]["firecrawl"]["env"]["FIRECRAWL_API_KEY"])
print("github placeholder:", d["mcpServers"]["github"]["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"])
