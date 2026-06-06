$ErrorActionPreference='Stop'
$bat='C:\Users\ma_py\OneDrive\デスクトップ\ses_work\wd_project_expiry.bat'
$a=New-ScheduledTaskAction -Execute $bat
$t=New-ScheduledTaskTrigger -Daily -At 7:00am
$s=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName 'SES_ProjectExpiry' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Output 'REGISTERED_OK'
