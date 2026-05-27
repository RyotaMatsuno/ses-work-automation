import os, sys, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Windowsの一般的なElectronアプリのログ場所を探す
patterns = [
    r"C:\Users\ma_py\AppData\Roaming\Claude\*",
    r"C:\Users\ma_py\AppData\Local\Temp\*mcp*",
    r"C:\Users\ma_py\AppData\Roaming\*claude*\*",
]

for pattern in patterns:
    matches = glob.glob(pattern, recursive=True)
    for m in matches[:20]:
        print(m)

# Claude Desktopのバージョン確認
import subprocess
result = subprocess.run(
    ['powershell', '-Command', 
     'Get-ItemProperty "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*" | Where-Object { $_.DisplayName -like "*Claude*" } | Select-Object DisplayName, DisplayVersion'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print("\n=== Claude バージョン ===")
print(result.stdout or "レジストリ未発見")
