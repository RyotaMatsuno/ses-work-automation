import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 実行中のnode.exeプロセスとその起動コマンドを確認
result = subprocess.run(
    ['powershell', '-Command',
     'Get-Process node -ErrorAction SilentlyContinue | ForEach-Object { $_.Id, $_.MainModule.FileName, (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine } | Out-String'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print("=== node.exeプロセス ===")
print(result.stdout or "node.exeプロセスなし")

# Claude.exeのプロセスも確認
result2 = subprocess.run(
    ['powershell', '-Command',
     'Get-Process -Name "Claude" -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, StartTime | Format-Table -AutoSize | Out-String'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print("=== Claude.exeプロセス ===")
print(result2.stdout or "Claude.exeプロセスなし")
