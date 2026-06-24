# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# スクリーンショットを撮ってses_workに保存
r = subprocess.run(
    [
        "powershell",
        "-Command",
        """
Add-Type -AssemblyName System.Windows.Forms
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bitmap.Save('C:\\Users\\ma_py\\OneDrive\\Desktop\\ses_work\\screenshot_now.png')
Write-Host "OK"
""",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=15,
)
print(r.stdout.strip())
print(r.stderr[:200] if r.stderr else "")
