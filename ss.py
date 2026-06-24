import subprocess

r = subprocess.run(
    [
        "powershell",
        "-Command",
        "Add-Type -AssemblyName System.Windows.Forms; $s=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; $b=New-Object System.Drawing.Bitmap($s.Width,$s.Height); $g=[System.Drawing.Graphics]::FromImage($b); $g.CopyFromScreen($s.Location,[System.Drawing.Point]::Empty,$s.Size); $b.Save('C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work\\screenshot_now.png'); Write-Host OK",
    ],
    capture_output=True,
    text=True,
    timeout=15,
)
print(r.stdout.strip())
