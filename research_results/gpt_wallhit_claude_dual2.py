import sys, os, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

api_key = "REDACTED_API_KEY"

import urllib.request

url = "https://api.openai.com/v1/responses"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

payload = {
    "model": "gpt-5.4",
    "input": [
        {
            "role": "developer",
            "content": "You are a Windows systems expert. Give concrete, tested solutions. No fluff. Reply in Japanese."
        },
        {
            "role": "user",
            "content": """Problem: Windows MSIX版Claude Desktopを2つ同時起動したい。

Current situation:
- Claude Desktop is MSIX package (PackageFamilyName: Claude_pzs8sxrjxfjjc)
- Install: C:\\Program Files\\WindowsApps\\Claude_1.15200.0.0_x64__pzs8sxrjxfjjc\\app\\claude.exe
- Electron app packaged as MSIX
- Running exe directly from WindowsApps with --user-data-dir: nothing happens
- start "" "path\\claude.exe" --user-data-dir="...": nothing happens

On Mac: open -n -a "Claude" --args --user-data-dir="..." works perfectly.

Questions:
1. Can --user-data-dir work with MSIX Electron apps on Windows?
2. If not, best alternative? Consider:
   a. Uninstall MSIX, install EXE/Squirrel version (but "Claude Setup.exe" from claude.com/download also installs as MSIX)
   b. Windows trick to launch MSIX with custom args
   c. Other approach
3. Any way to get a non-MSIX Windows installer for Claude Desktop?

Give the most practical working solution with exact commands."""
        }
    ],
    "reasoning": {"effort": "low"},
    "max_output_tokens": 4000
}

req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        for item in data.get('output', []):
            if item.get('type') == 'message':
                for content in item.get('content', []):
                    if content.get('type') == 'output_text':
                        print(content['text'])
except Exception as e:
    print(f"Error: {e}")
