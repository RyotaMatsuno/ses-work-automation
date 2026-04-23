# SES Task Scheduler Setup
# Run this in PowerShell as Administrator

$python = "C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"
$base = "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
$outlook = "$base\outlook\outlook_to_notion.py"
$freee = "$base\freee\freee_invoice.py"

Write-Host "=== SES Task Setup ===" -ForegroundColor Cyan

# Outlook x3
foreach ($hour in @("09:00", "13:00", "18:00")) {
    $tag = $hour -replace ":", ""
    $name = "SES_Outlook_$tag"
    $action = New-ScheduledTaskAction -Execute $python -Argument "`"$outlook`""
    $trigger = New-ScheduledTaskTrigger -Daily -At $hour
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1)
    Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null
    Write-Host "OK: $name ($hour)" -ForegroundColor Green
}

# Freee monthly
$fname = "SES_Freee_Invoice"
$faction = New-ScheduledTaskAction -Execute $python -Argument "`"$freee`""
$ftrigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 4 -DaysOfWeek Monday -At "10:00"
$fsettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName $fname -Action $faction -Trigger $ftrigger -Settings $fsettings -RunLevel Highest -Force | Out-Null
Write-Host "OK: $fname (monthly ~25th)" -ForegroundColor Green

Write-Host ""
Write-Host "All tasks registered!" -ForegroundColor Cyan
Write-Host "Verify: Get-ScheduledTask | Where-Object {`$_.TaskName -like 'SES_*'}"
Read-Host "Press Enter to exit"
