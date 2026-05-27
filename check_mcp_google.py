import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')

mcp_paths = [
    r'C:\Users\ma_py\AppData\Roaming\Claude\claude_desktop_config.json',
    r'C:\Users\ma_py\.config\claude\claude_desktop_config.json',
]

for path in mcp_paths:
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        print(f"found: {path}", flush=True)
        for key, val in data.get('mcpServers', {}).items():
            env = val.get('env', {})
            args = val.get('args', [])
            print(f"  server: {key}", flush=True)
            for k, v in env.items():
                if 'google' in k.lower() or 'client' in k.lower() or 'token' in k.lower() or 'secret' in k.lower():
                    print(f"    {k}: {str(v)[:40]}...", flush=True)
        break
else:
    print("config not found", flush=True)
