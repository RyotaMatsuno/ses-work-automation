import subprocess, os

bat_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\cloudflare\run_tunnel.bat"
startup_dir = r"C:\Users\ma_py\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
link_path = os.path.join(startup_dir, "jobz_tunnel.lnk")

# PowerShellでショートカット作成
ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{link_path}')
$s.TargetPath = '{bat_path}'
$s.WindowStyle = 7
$s.Description = 'Jobz Quick Tunnel'
$s.Save()
Write-Host "Created: {link_path}"
"""

r = subprocess.run(
    ["powershell", "-Command", ps_script],
    capture_output=True, text=True, timeout=15
)
print(r.stdout)
if r.returncode != 0:
    print(f"ERROR: {r.stderr[:200]}")
else:
    print("スタートアップ登録完了")
