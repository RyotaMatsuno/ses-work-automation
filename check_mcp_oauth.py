
import json

# GCPコンソールのスクショで確認済みのclient_id
# 74735301292-op9eiut55pjdkhb44p25c6hlokcf01ql.apps.googleusercontent.com
# client_secretはコンソールから取得が必要だが、別の方法で対応

# 方針変更: OAuth2 PKCE不要のDesktopアプリフロー
# client_secretはpublicなデスクトップアプリでは取得可能
# -> GCPコンソールのAPIで取得する代わりに、
#    既存のGmail MCPの設定からclient情報を探す

import os

mcp_config = r"C:\Users\ma_py\AppData\Roaming\Claude\claude_desktop_config.json"
with open(mcp_config, "r", encoding="utf-8") as f:
    config = json.load(f)

print("MCP servers:")
for k, v in config.get("mcpServers", {}).items():
    env = v.get("env", {})
    args = v.get("args", [])
    print(f"\n[{k}]")
    if env:
        for ek, ev in env.items():
            if "secret" in ek.lower() or "key" in ek.lower() or "token" in ek.lower():
                print(f"  {ek}: {str(ev)[:30]}...")
            else:
                print(f"  {ek}: {ev}")
