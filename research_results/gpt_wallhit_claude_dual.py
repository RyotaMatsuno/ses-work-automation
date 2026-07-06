import sys, os, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Load API key
with open('config/.env', 'r') as f:
    for line in f:
        if line.startswith('OPENAI_API_KEY='):
            api_key = line.strip().split('=', 1)[1]
            break

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
            "content": "You are a Windows systems expert. Give concrete, tested solutions. No fluff."
        },
        {
            "role": "user",
            "content": """Problem: I need to run TWO instances of Claude Desktop simultaneously on Windows.

Current situation:
- Claude Desktop is installed as MSIX package (Microsoft Store / Appx format)
- Package: Claude_pzs8sxrjxfjjc
- Install location: C:\\Program Files\\WindowsApps\\Claude_1.15200.0.0_x64__pzs8sxrjxfjjc\\app\\claude.exe
- It's an Electron app packaged as MSIX
- I tried running the exe directly from WindowsApps with --user-data-dir flag but nothing happens
- batファイルからstart "" "path\\to\\claude.exe" --user-data-dir="..." としても何も起動しない

What I tried that failed:
1. Direct exe execution from WindowsApps folder - no response
2. PowerShell Get-AppxPackage + Start-Process with --user-data-dir - no response
3. The exe path exists and is visible in Explorer

On Mac, this works easily: open -n -a "Claude" --args --user-data-dir="..."

Questions:
1. Is it possible to pass --user-data-dir to an MSIX-packaged Electron app on Windows?
2. If not, what's the best way to run two instances? Options I'm considering:
   a. Uninstall MSIX and install the EXE/Squirrel version instead
   b. Some Windows trick to launch MSIX apps with custom args
   c. Using AppExecAlias or other mechanism
3. If option (a), how do I get the non-MSIX installer? The "Claude Setup.exe" from claude.com/download seems to install as MSIX anyway (version went from 1.14271 to 1.15200 when I ran it)

Give me the most practical working solution."""
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
